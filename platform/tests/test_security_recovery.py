import csv
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections, transaction, DatabaseError
from django.urls import reverse
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from core.models import RoleGrant, AuditLog, PrivacyRequest
from core.privacy import anonymize_attendee
from admissions.models import Ticket, CheckIn
from admissions.services import set_entry_mode, committed
from admissions.imports import preview_import, commit_import
from operations.models import Task
from team.models import Department, Volunteer, Membership
from .test_admission import allocate


@pytest.mark.django_db(transaction=True)
def test_twenty_concurrent_allocations_one_remaining(event, organizer):
    event.capacity = 1
    event.save()
    def register_one(index):
        try:
            allocate(event, organizer, f"fixture{index}@example.invalid")
            return "registered"
        except ValidationError:
            return "full"
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=5) as pool:
        states = list(pool.map(register_one, range(20)))
    assert states.count("registered") == 1
    assert states.count("full") == 19
    assert Ticket.objects.filter(event=event).count() == 1


@pytest.mark.django_db
def test_mfa_enrollment_and_replay(client, event, organizer, settings):
    settings.MFA_REQUIRED = True
    client.force_login(organizer)
    assert client.post(reverse("mfa"), {"action": "enroll"}).status_code == 302
    device = TOTPDevice.objects.get(user=organizer)
    code = totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift)
    response = client.post(reverse("mfa"), {"code": str(code).zfill(6)})
    assert b"Save your recovery codes" in response.content
    assert client.get(reverse("dashboard", args=[event.slug])).status_code == 200
    response = client.post(reverse("mfa"), {"code": str(code).zfill(6)})
    assert b"Invalid or already-used code" in response.content


@pytest.mark.django_db
def test_leader_and_volunteer_roles_do_not_combine_scopes(client, event, settings):
    settings.MFA_REQUIRED = False
    user = get_user_model().objects.create_user("mixed")
    a = Department.objects.create(event=event, name="A")
    b = Department.objects.create(event=event, name="B")
    RoleGrant.objects.create(event=event, user=user, role="leader", department=a, reason="Test")
    RoleGrant.objects.create(event=event, user=user, role="volunteer", reason="Test")
    volunteer = Volunteer.objects.create(event=event, user=user, name="Mixed", email="mixed@example.invalid")
    Membership.objects.create(event=event, department=b, volunteer=volunteer, supervisor=user)
    task = Task.objects.create(
        event=event, department=b, owner=user, title="Assigned in B", acceptance="Done"
    )
    client.force_login(user)
    response = client.post(
        reverse("resource-edit", args=[event.slug, "tasks", task.pk]),
        {"title": "Unauthorized rewrite", "status": "completed", "version": 1},
    )
    assert response.status_code == 302
    task.refresh_from_db()
    assert task.title == "Assigned in B"
    assert task.status == "needs_review"


@pytest.mark.django_db
def test_audit_and_admission_are_immutable_in_database(event, organizer):
    record = AuditLog.objects.create(event=event, actor=organizer, action="test")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=record.pk).update(action="tampered")


@pytest.mark.django_db
def test_manual_ledger_repeat_and_freeze(event, organizer):
    ticket, _ = allocate(event, organizer)
    set_entry_mode(event, organizer, "online", "Open controlled test entrance")
    set_entry_mode(event, organizer, "manual", "Network outage; one supervised desk")
    event.refresh_from_db()
    with pytest.raises(ValidationError):
        from admissions.services import rotate_ticket

        rotate_ticket(event, organizer, ticket.pk, "Cannot rotate while manual")
    set_entry_mode(event, organizer, "reconciling", "All manual sheets collected")
    event.refresh_from_db()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["reference", "ledger_id", "admitted_at", "reason"])
    writer.writerow(
        [ticket.reference, "desk-one-001", timezone.now().isoformat(), "Supervisor physical admission"]
    )
    batch = preview_import(event, organizer, buffer.getvalue().encode(), "ledger")
    commit_import(event, organizer, batch.pk, "Reviewed ledger")
    commit_import(event, organizer, batch.pk, "Retry")
    assert CheckIn.objects.filter(ticket=ticket).count() == 1
    assert committed(event) == 1


@pytest.mark.django_db
def test_privacy_hold_then_anonymization(event, organizer):
    ticket, _ = allocate(event, organizer)
    event.registration_mode = "closed"
    event.admission_opens_at = None
    event.starts_at = timezone.now() - timedelta(days=100, hours=3)
    event.ends_at = timezone.now() - timedelta(days=100)
    event.save()
    item = PrivacyRequest.objects.create(
        event=event,
        email=ticket.attendee.email,
        kind="erase",
        status="verified",
        hold_until=timezone.now() + timedelta(days=1),
    )
    with pytest.raises(ValidationError):
        anonymize_attendee(event, organizer, item.pk, "Approved")
    event.retention_days = 90
    event.retention_reason = "Survey completed; event dispute period reviewed"
    event.save()
    item.hold_until = None
    item.save()
    anonymize_attendee(event, organizer, item.pk, "Verified request, retention elapsed")
    ticket.attendee.refresh_from_db()
    assert ticket.attendee.email is None
    assert ticket.attendee.name == "Anonymized attendee"
    assert Ticket.objects.filter(pk=ticket.pk).exists()


@pytest.mark.django_db
def test_public_and_auth_pages_without_event(client):
    assert client.get("/").status_code == 200
    assert client.get("/accounts/login/").status_code == 200
