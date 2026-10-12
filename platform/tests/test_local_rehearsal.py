from datetime import timedelta
import uuid
import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.utils import timezone
from django.urls import reverse
from admissions.services import check_in
from admissions.models import Ticket
from tests.test_immediate_ticketing import register, raw


@pytest.fixture
def rehearsal(settings, no_local_rehearsal):
    settings.DEBUG = True
    settings.PRODUCTION = False
    settings.DEV_EVENT_REHEARSAL = True
    settings.DEV_LOGIN_EVENT = "test"
    settings.ALLOWED_HOSTS = ["localhost", "testserver"]


@pytest.mark.django_db
def test_rehearsal_opens_timing_without_disabling_ticket_integrity(event, organizer, rehearsal, settings):
    now = timezone.now()
    event.setup_at = now + timedelta(minutes=10)
    event.admission_opens_at = now + timedelta(minutes=20)
    event.opens_at = now + timedelta(minutes=10)
    event.promotions_cutoff = now - timedelta(minutes=1)
    event.entry_mode = "online"
    event.save()
    ticket = register(event).ticket
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw(ticket))["code"] == "VALID"
    assert (
        check_in(event, organizer, request_id=uuid.uuid4(), credential=raw(ticket))["code"]
        == "ALREADY_CHECKED_IN"
    )
    with pytest.raises(ValidationError, match="already registered"):
        register(event)
    second = register(event, "second@example.invalid").ticket
    with pytest.raises(ValidationError, match="full"):
        register(event, "third@example.invalid")
    Ticket.objects.filter(pk=second.pk).update(expires_at=now - timedelta(seconds=1))
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw(second))["code"] == "EXPIRED"
    settings.DEV_EVENT_REHEARSAL = False
    with pytest.raises(ValidationError, match="opening period"):
        register(event, "outside@example.invalid")


@pytest.mark.django_db
def test_prepare_uses_source_defaults_and_preserves_records(event, rehearsal):
    ticket = register(event).ticket
    original_notice = event.privacy_notice
    call_command("prepare_local_rehearsal")
    event.refresh_from_db()
    assert timezone.localtime(event.starts_at).strftime("%Y-%m-%d %H:%M") == "2026-11-21 13:00"
    assert timezone.localtime(event.setup_at).strftime("%H:%M") == "12:00"
    assert timezone.localtime(event.admission_opens_at).strftime("%H:%M") == "12:45"
    assert timezone.localtime(event.ends_at).strftime("%H:%M") == "16:00"
    assert event.entry_mode == "online" and event.privacy_notice == original_notice
    assert Ticket.objects.filter(pk=ticket.pk).exists()
    call_command("prepare_local_rehearsal")
    assert Ticket.objects.count() == 1


@pytest.mark.django_db
def test_rehearsal_never_fabricates_notice_approval(event, rehearsal):
    event.privacy_approved = False
    event.save()
    with pytest.raises(CommandError, match="approved notice"):
        call_command("prepare_local_rehearsal")
    with pytest.raises(ValidationError, match="approved KVKK"):
        register(event)


@pytest.mark.django_db
def test_rehearsal_is_local_and_has_visible_banner(event, rehearsal, client, settings):
    url = reverse("register", args=[event.slug])
    response = client.get(url, HTTP_HOST="localhost")
    assert response.status_code == 200 and b"YEREL TEST MODU" in response.content
    assert client.get(url, HTTP_HOST="localhost", REMOTE_ADDR="192.168.1.2").status_code == 404
    assert client.get(url, HTTP_HOST="localhost", HTTP_X_FORWARDED_FOR="127.0.0.1").status_code == 404
    settings.PRODUCTION = True
    assert client.get(url, HTTP_HOST="localhost").status_code == 404
    with pytest.raises(CommandError):
        call_command("prepare_local_rehearsal")
