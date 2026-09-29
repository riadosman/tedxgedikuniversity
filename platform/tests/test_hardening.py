import hashlib
import subprocess
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.urls import reverse
from core.models import RoleGrant
from documents.models import Document


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        "event_admin",
        "technology",
        "leader",
        "volunteer",
        "checkin",
        "speaker_manager",
        "editor",
        "finance",
        "speaker",
    ],
)
def test_roles_cannot_escalate_or_cross_event(client, event, settings, role):
    from team.models import Department

    settings.MFA_REQUIRED = False
    user = get_user_model().objects.create_user("boundary-" + role)
    department = Department.objects.create(event=event, name="Boundary") if role == "leader" else None
    RoleGrant.objects.create(event=event, user=user, role=role, department=department, reason="Test scope")
    client.force_login(user)
    assert client.get(reverse("resource-create", args=[event.slug, "roles"])).status_code == 403
    assert client.post(reverse("event-settings", args=[event.slug]), {"published": "on"}).status_code == 403
    assert client.get(reverse("dashboard", args=[event.slug])).status_code == 200
    from core.models import Event

    other = Event.objects.create(
        name="Other isolated event",
        slug="other",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        licensed_capacity=100,
    )
    assert client.get(reverse("dashboard", args=[other.slug])).status_code == 403
    user.is_active = False
    user.save()
    assert client.get(reverse("dashboard", args=[event.slug])).status_code == 302


@pytest.mark.django_db
def test_upload_malformed_and_denied_cleanup(client, event, organizer, settings, tmp_path):
    settings.MFA_REQUIRED = False
    settings.MEDIA_ROOT = tmp_path
    settings.FILE_SCAN_COMMAND = ""
    client.force_login(organizer)
    url = reverse("resource-create", args=[event.slug, "files"])
    response = client.post(
        url,
        {
            "title": "Malformed",
            "scope": "leadership",
            "file": SimpleUploadedFile("broken.pptx", b"PK\x03\x04not-a-zip"),
        },
    )
    assert response.status_code == 200
    assert not Document.objects.exists()
    editor = get_user_model().objects.create_user("file-editor")
    RoleGrant.objects.create(event=event, user=editor, role="editor", reason="Test")
    client.force_login(editor)
    response = client.post(
        url,
        {
            "title": "Denied scope",
            "scope": "leadership",
            "file": SimpleUploadedFile("test.pdf", b"%PDF-1.4\nfixture"),
        },
    )
    assert response.status_code == 403
    assert not Document.objects.exists()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


@pytest.mark.django_db
def test_quarantine_release_requires_scanner_and_preserves_integrity(event, organizer, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    path = tmp_path / "fixture.pdf"
    content = b"%PDF-1.4\nquarantine-test"
    path.write_bytes(content)
    document = Document.objects.create(
        event=event,
        title="Fixture",
        original_name="fixture.pdf",
        storage_key="fixture.pdf",
        content_type="application/pdf",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        uploader=organizer,
    )
    settings.FILE_SCAN_COMMAND = ""
    with pytest.raises(CommandError):
        call_command("scan_documents")
    settings.FILE_SCAN_COMMAND = "configured-scanner"
    with patch(
        "documents.management.commands.scan_documents.subprocess.run",
        return_value=subprocess.CompletedProcess([], 2),
    ):
        call_command("scan_documents")
    document.refresh_from_db()
    assert document.scan_status == "quarantined"
    with patch(
        "documents.management.commands.scan_documents.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
    ) as runner:
        call_command("scan_documents")
    runner.assert_called_once()
    document.refresh_from_db()
    assert document.scan_status == "clean"
    document.scan_status = "quarantined"
    document.save()
    path.write_bytes(b"altered")
    with patch("documents.management.commands.scan_documents.subprocess.run") as runner:
        call_command("scan_documents")
    runner.assert_not_called()
    document.refresh_from_db()
    assert document.scan_status == "rejected"


@pytest.mark.django_db
def test_registration_uses_configured_general_category(client, event, organizer, settings):
    from admissions.models import TicketType
    from tests.test_admission import allocate
    category = TicketType.objects.get(event=event, code="general")
    category.name = "Configured admission"
    category.save()
    ticket, _ = allocate(event, organizer)
    assert ticket.ticket_type_id == category.pk
