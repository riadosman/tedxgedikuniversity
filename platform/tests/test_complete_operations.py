from datetime import timedelta
import json
import uuid
from cryptography.fernet import Fernet
import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import RoleGrant, AccountInvitation
from core.workflows import action_resource
from team.models import VolunteerApplication, Volunteer, Department, Membership, Shift, ShiftAssignment
from program.models import Speaker, Talk, ScheduleItem
from operations.models import Incident, RunbookItem, RunbookAcknowledgment, Task
from communications.models import Announcement, AnnouncementRead, Notification
from documents.models import Document


@pytest.mark.django_db
def test_team_program_and_operations_rehearsal(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    event.volunteer_open = True
    event.max_talk_minutes = 18
    event.save()
    from admissions.models import Registration, Ticket, Credential
    from admissions.services import new_action_token

    from admissions.services import notice_digest
    response = client.post(reverse("register", args=[event.slug]), {
        "name": "Rehearsal attendee", "email": "attendee@example.invalid", "privacy": "on",
        "notice_version": event.notice_version, "notice_hash": notice_digest(event),
    })
    assert response.status_code == 302
    registration = Registration.objects.get(attendee__email="attendee@example.invalid")
    ticket = Ticket.objects.get(registration=registration)
    raw = (
        Fernet(settings.CREDENTIAL_KEY.encode())
        .decrypt(Credential.objects.get(ticket=ticket).ciphertext.encode())
        .decode()
    )
    access = new_action_token(ticket.attendee)
    qr = client.get(reverse("ticket-qr", args=[event.slug, access]))
    assert qr.status_code == 200 and qr.content.startswith(b"\x89PNG")
    client.logout()
    response = client.post(
        reverse("volunteer-apply", args=[event.slug]),
        {
            "name": "Rehearsal volunteer",
            "email": "volunteer@example.invalid",
            "availability": "Event day",
            "privacy": "on",
        },
    )
    assert response.status_code == 200
    application = VolunteerApplication.objects.get(email="volunteer@example.invalid")
    client.force_login(organizer)
    response = client.post(
        reverse("resource-action", args=[event.slug, "applications", application.pk, "accepted"]),
        {"reason": "Interview completed"},
    )
    assert response.status_code == 302
    volunteer = Volunteer.objects.get(application=application)
    assert volunteer.user_id is None
    assert not RoleGrant.objects.filter(role="volunteer").exists()
    response = client.post(
        reverse("invite-user", args=[event.slug]),
        {"username": "rehearsal-volunteer", "email": volunteer.email, "first_name": "Rehearsal"},
    )
    assert response.status_code == 302
    user = get_user_model().objects.get(username="rehearsal-volunteer")
    assert not user.has_usable_password()
    assert AccountInvitation.objects.filter(event=event, user=user).exists()
    response = client.post(
        reverse("resource-create", args=[event.slug, "roles"]),
        {"user": user.pk, "role": "volunteer", "active": "on", "reason": "Accepted volunteer"},
    )
    assert response.status_code == 302
    volunteer.user = user
    volunteer.save()
    dept = Department.objects.create(event=event, name="Rehearsal production")
    Membership.objects.create(event=event, department=dept, volunteer=volunteer, supervisor=organizer)
    response = client.post(
        reverse("resource-create", args=[event.slug, "tasks"]),
        {
            "title": "Prepare entrance",
            "department": dept.pk,
            "owner": user.pk,
            "priority": "high",
            "status": "not_started",
            "acceptance": "Scanner verified",
        },
    )
    assert response.status_code == 302
    assert Task.objects.get(title="Prepare entrance").owner_id == user.pk
    shift = Shift.objects.create(
        event=event,
        department=dept,
        title="Opening shift",
        starts_at=event.setup_at,
        ends_at=event.ends_at,
        location="Test venue",
    )
    assignment = ShiftAssignment.objects.create(event=event, shift=shift, volunteer=volunteer)
    action_resource(event, organizer, "assignments", assignment.pk, "brief", "Briefing complete")
    client.force_login(user)
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "assignments", assignment.pk, "acknowledge"]),
            {"reason": "Available"},
        ).status_code
        == 302
    )
    assignment.refresh_from_db()
    assert assignment.acknowledged_at and assignment.briefed_at
    client.force_login(organizer)
    speaker = Speaker.objects.create(
        event=event,
        name="Rehearsal speaker",
        status="confirmed",
        biography="Synthetic test biography",
        publication_consent=True,
    )
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "speakers", speaker.pk, "publish"]),
            {"reason": "Approved public profile"},
        ).status_code
        == 302
    )
    talk = Talk.objects.create(
        event=event,
        speaker=speaker,
        title="Rehearsal talk",
        release_received=True,
        fact_checked=True,
        rights_cleared=True,
        status="ready",
    )
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "talks", talk.pk, "approve"]),
            {"reason": "Review complete"},
        ).status_code
        == 302
    )
    response = client.post(
        reverse("resource-create", args=[event.slug, "schedule"]),
        {
            "title": "Opening talk",
            "kind": "talk",
            "talk": talk.pk,
            "starts_at": event.starts_at.isoformat(),
            "ends_at": (event.starts_at + timedelta(minutes=15)).isoformat(),
            "public_description": "Approved test session",
        },
    )
    assert response.status_code == 302, response.content.decode()[:4000]
    session = ScheduleItem.objects.get(talk=talk)
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "schedule", session.pk, "publish"]),
            {"reason": "Schedule approved"},
        ).status_code
        == 302
    )
    runbook = RunbookItem.objects.create(
        event=event, title="Sound cue", instructions="Use the approved test cue", audience="staff"
    )
    action_resource(event, organizer, "runbook", runbook.pk, "publish", "Production ready")
    client.force_login(user)
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "runbook", runbook.pk, "acknowledge"]), {}
        ).status_code
        == 302
    )
    assert RunbookAcknowledgment.objects.filter(item=runbook, user=user).exists()
    client.force_login(organizer)
    response = client.post(
        reverse("resource-create", args=[event.slug, "incidents"]),
        {
            "title": "Test microphone fault",
            "description": "Synthetic rehearsal problem",
            "category": "technical",
            "severity": "high",
            "status": "open",
        },
    )
    assert response.status_code == 302
    incident = Incident.objects.get(title="Test microphone fault")
    response = client.post(
        reverse("resource-edit", args=[event.slug, "incidents", incident.pk]),
        {
            "title": incident.title,
            "description": incident.description,
            "category": "technical",
            "severity": "high",
            "status": "resolved",
            "resolution": "Backup microphone tested",
            "version": 1,
        },
    )
    assert response.status_code == 302
    incident.refresh_from_db()
    assert incident.status == "resolved"
    announcement = Announcement.objects.create(
        event=event,
        title="Rehearsal update",
        body="Synthetic team announcement",
        audience="volunteers",
        publish_at=timezone.now(),
    )
    action_resource(
        event, organizer, "announcements", announcement.pk, "publish", "Notify assigned volunteers"
    )
    assert Notification.objects.filter(template_key="announcement", recipient=volunteer.email).exists()
    client.force_login(user)
    assert (
        client.post(
            reverse("resource-action", args=[event.slug, "announcements", announcement.pk, "read"]), {}
        ).status_code
        == 302
    )
    assert AnnouncementRead.objects.filter(announcement=announcement, user=user).exists()
    client.force_login(organizer)
    event.entry_mode = "online"
    event.save()
    endpoint = reverse("scan-api", args=[event.slug])
    for expected in ["VALID", "ALREADY_CHECKED_IN"]:
        result = client.post(
            endpoint,
            json.dumps({"request_id": str(uuid.uuid4()), "credential": raw}),
            content_type="application/json",
        )
        assert result.json()["code"] == expected
    lookup = client.get(reverse("scanner-data", args=[event.slug]), {"q": "Rehearsal attendee"}).json()
    assert len(lookup["matches"]) == 1 and lookup["checked_in"] == 1
    report = client.get(reverse("reports", args=[event.slug]))
    assert report.status_code == 200 and report.context["checked_in"] == 1 and report.context["no_shows"] == 0
    exported = client.post(
        reverse("resource-export", args=[event.slug, "checkins"]), {"reason": "Post-event rehearsal report"}
    )
    assert exported.status_code == 200 and exported["Content-Type"].startswith("text/csv")


@pytest.mark.django_db
def test_private_upload_quarantine_and_access(client, event, organizer, settings, tmp_path):
    settings.MFA_REQUIRED = False
    settings.MEDIA_ROOT = tmp_path
    settings.FILE_SCAN_COMMAND = ""
    client.force_login(organizer)
    upload = SimpleUploadedFile("test.pdf", b"%PDF-1.4\nSynthetic fixture\n", content_type="application/pdf")
    response = client.post(
        reverse("resource-create", args=[event.slug, "files"]),
        {"title": "Private rehearsal document", "scope": "leadership", "file": upload},
    )
    assert response.status_code == 302, response.content.decode()[:4000]
    document = Document.objects.get(title="Private rehearsal document")
    assert document.scan_status == "quarantined"
    assert client.get(reverse("file-download", args=[event.slug, document.pk])).status_code == 404
    client.logout()
    assert client.get(reverse("file-download", args=[event.slug, document.pk])).status_code == 302
    assert client.get(reverse("public-image", args=[event.slug, document.pk])).status_code == 404


@pytest.mark.django_db
def test_published_runbook_draft_is_not_visible_to_volunteer(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    user = get_user_model().objects.create_user("reader")
    RoleGrant.objects.create(event=event, user=user, role="volunteer", reason="Rehearsal")
    item = RunbookItem.objects.create(
        event=event, title="Approved cue", instructions="Published instruction", audience="staff"
    )
    action_resource(event, organizer, "runbook", item.pk, "publish", "Approved")
    item.refresh_from_db()
    item.title = "Private draft title"
    item.instructions = "Unapproved private cue"
    item.save()
    client.force_login(user)
    response = client.get(reverse("resource-detail", args=[event.slug, "runbook", item.pk]))
    assert b"Published instruction" in response.content
    assert b"Unapproved private cue" not in response.content
    assert b"Private draft title" not in response.content
