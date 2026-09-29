import uuid
from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from core.models import RoleGrant, Page
from core.forms import resource_form
from core.resources import RESOURCES
from core.workflows import save_resource, action_resource
from team.models import Department, Volunteer, Membership, Shift, ShiftAssignment
from operations.models import Task, TaskDependency
from communications.models import NotificationTemplate, Notification
from communications.services import enqueue, deliver_batch
from admissions.services import submit_registration, notice_digest
from admissions.models import Attendee


@pytest.fixture
def signed_client(client, organizer, settings):
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    return client


@pytest.mark.django_db
def test_staff_routes_render(signed_client, event):
    for key in RESOURCES:
        response = signed_client.get(reverse("resource-list", args=[event.slug, key]))
        assert response.status_code == 200, (key, response.status_code)
    for route in ["dashboard", "scanner", "reports", "event-settings", "users"]:
        assert signed_client.get(reverse(route, args=[event.slug])).status_code == 200


@pytest.mark.django_db
def test_create_edit_task_and_stale_version(signed_client, event, organizer):
    url = reverse("resource-create", args=[event.slug, "tasks"])
    data = {
        "title": "Confirm microphones",
        "description": "Test at venue",
        "priority": "high",
        "status": "not_started",
        "acceptance": "Both microphones audible",
    }
    response = signed_client.post(url, data)
    assert response.status_code == 302, response.content.decode()[:3000]
    task = Task.objects.get(title=data["title"])
    data.update(title="Confirm backup microphones", version=1)
    url = reverse("resource-edit", args=[event.slug, "tasks", task.pk])
    assert signed_client.post(url, data).status_code == 302
    response = signed_client.post(url, {**data, "title": "Stale edit"})
    assert response.status_code == 200
    task.refresh_from_db()
    assert task.title == "Confirm backup microphones"
    assert b"changed while" in response.content


@pytest.mark.django_db
def test_leader_scope_and_checkin_no_export(client, event, settings):
    settings.MFA_REQUIRED = False
    user = get_user_model().objects.create_user("leader")
    own = Department.objects.create(event=event, name="Own department")
    other = Department.objects.create(event=event, name="Other department")
    RoleGrant.objects.create(event=event, user=user, role="leader", department=own, reason="Test")
    task = Task.objects.create(event=event, title="Private task", department=other, acceptance="Done")
    client.force_login(user)
    assert client.get(reverse("resource-detail", args=[event.slug, "tasks", task.pk])).status_code == 404
    assert client.get(reverse("resource-export", args=[event.slug, "tasks"])).status_code == 403
    response = client.post(
        reverse("resource-create", args=[event.slug, "tasks"]),
        {
            "title": "Intrusion",
            "department": other.pk,
            "priority": "normal",
            "status": "not_started",
            "acceptance": "Done",
        },
    )
    assert response.status_code == 200
    assert not Task.objects.filter(title="Intrusion").exists()
    RoleGrant.objects.create(event=event, user=user, role="checkin", reason="Test")
    assert client.get(reverse("scanner", args=[event.slug])).status_code == 200
    assert client.get(reverse("resource-list", args=[event.slug, "attendees"])).status_code == 403


@pytest.mark.django_db
def test_task_dependency_cycle_and_shift_overlap(event, organizer):
    one = Task.objects.create(event=event, title="One", acceptance="Done")
    two = Task.objects.create(event=event, title="Two", acceptance="Done")
    TaskDependency.objects.create(event=event, task=one, depends_on=two)
    form = resource_form(RESOURCES["dependencies"], organizer, event, {"task": two.pk, "depends_on": one.pk})
    assert form.is_valid(), form.errors
    with pytest.raises(ValidationError):
        save_resource(event, organizer, "dependencies", form)
    dept = Department.objects.create(event=event, name="Production")
    volunteer = Volunteer.objects.create(event=event, name="Test", email="volunteer@example.invalid")
    Membership.objects.create(event=event, department=dept, volunteer=volunteer, supervisor=organizer)
    first = Shift.objects.create(
        event=event,
        department=dept,
        title="Morning",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=2),
        location="Test room",
    )
    second = Shift.objects.create(
        event=event,
        department=dept,
        title="Overlap",
        starts_at=first.starts_at,
        ends_at=first.ends_at,
        location="Test room",
    )
    ShiftAssignment.objects.create(event=event, shift=first, volunteer=volunteer)
    with pytest.raises(ValidationError):
        ShiftAssignment.objects.create(event=event, shift=second, volunteer=volunteer)


@pytest.mark.django_db
def test_public_snapshot_and_xss(client, event, organizer):
    page = Page.objects.create(
        event=event, key="about", title="Approved title", body="<script>alert(1)</script>"
    )
    action_resource(event, organizer, "pages", page.pk, "publish", "Reviewed")
    page.refresh_from_db()
    page.title = "Unapproved title"
    page.save()
    response = client.get(reverse("public-page", args=[event.slug, "about"]))
    assert b"Approved title" in response.content and b"Unapproved title" not in response.content
    assert b"<script>alert(1)</script>" not in response.content
    assert b"&lt;script&gt;" in response.content


@pytest.mark.django_db
def test_registration_duplicate_generic_and_tokens(client, event):
    registration = submit_registration(event, name="Person", email="person@example.invalid",
        privacy_acknowledged=True, notice_version=event.notice_version, notice_hash=notice_digest(event))
    with pytest.raises(ValidationError, match="already registered"):
        submit_registration(event, name="Other", email="PERSON@example.invalid",
            privacy_acknowledged=True, notice_version=event.notice_version, notice_hash=notice_digest(event))
    assert Attendee.objects.filter(event=event).count() == 1
    assert registration.ticket.status == "registered"
    assert registration.attendee.verified_at is None


@pytest.mark.django_db
def test_outbox_idempotency_and_delivery(event, settings, mailoutbox):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    NotificationTemplate.objects.create(
        event=event, key="test", subject="Update — {event}", body="Hello {name}: {status}"
    )
    for _ in range(2):
        enqueue(event, "person@example.invalid", "test", {"name": "Person", "status": "approved"}, "same-key")
    assert Notification.objects.count() == 1
    assert deliver_batch() == 1
    assert len(mailoutbox) == 1
    assert deliver_batch() == 0


@pytest.mark.django_db
def test_mfa_required_and_csrf(client, event, organizer, settings):
    settings.MFA_REQUIRED = True
    client.force_login(organizer)
    assert client.get(reverse("dashboard", args=[event.slug])).url == reverse("mfa")
    from django.test import Client

    strict = Client(enforce_csrf_checks=True)
    strict.force_login(organizer)
    settings.MFA_REQUIRED = False
    response = strict.post(
        reverse("scan-api", args=[event.slug]),
        {"request_id": str(uuid.uuid4())},
        content_type="application/json",
    )
    assert response.status_code == 403
