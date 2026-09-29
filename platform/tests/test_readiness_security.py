import json
import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from django.db import connections, transaction, connection, IntegrityError
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import RoleGrant, Event
from admissions.models import CheckIn, Registration, Attendee
from admissions.services import check_in, new_action_token
from .test_admission import allocate


def test_production_settings_gate(settings):
    import os
    import subprocess
    import sys
    from cryptography.fernet import Fernet

    env = dict(os.environ)
    env.update(
        DJANGO_ENV="production",
        DJANGO_SECRET_KEY="test-only-secret-" * 8,
        CREDENTIAL_KEY=Fernet.generate_key().decode(),
        PUBLIC_BASE_URL="https://rehearsal.example.invalid",
        ALLOWED_HOSTS="rehearsal.example.invalid",
        CSRF_TRUSTED_ORIGINS="https://rehearsal.example.invalid",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.example.invalid",
        DEFAULT_FROM_EMAIL="event@example.invalid",
        EMAIL_USE_TLS="true",
        MFA_REQUIRED="true",
        HSTS_PRELOAD="false",
        HSTS_INCLUDE_SUBDOMAINS="false",
    )
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    env["EMAIL_BACKEND"] = "django.core.mail.backends.filebased.EmailBackend"
    rejected = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert rejected.returncode != 0


def test_traceback_logging_redacts_private_values():
    import logging
    from core.logging import RedactingFormatter

    credential = "tx1." + str(uuid.uuid4()) + ".credential"
    try:
        raise ValueError("private@example.invalid " + credential)
    except ValueError:
        import sys

        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "Failure", (), sys.exc_info())
    text = RedactingFormatter().format(record)
    assert "private@example.invalid" not in text and credential not in text
    assert "[email-redacted]" in text and "[qr-redacted]" in text


@pytest.mark.django_db
def test_cannot_deactivate_account_serving_another_event(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    other = Event.objects.create(
        name="Other test event",
        slug="other",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        licensed_capacity=100,
    )
    target = get_user_model().objects.create_user("shared", password="Test-only-password-827")
    RoleGrant.objects.create(event=event, user=target, role="checkin", reason="Test")
    RoleGrant.objects.create(event=other, user=target, role="checkin", reason="Test")
    client.force_login(organizer)
    response = client.post(reverse("users", args=[event.slug]), {"user": target.pk, "reason": "Test"})
    assert response.status_code == 302
    target.refresh_from_db()
    assert target.is_active


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "text",
        {"request_id": "bad"},
        {"request_id": str(uuid.uuid4()), "credential": {}},
        {"request_id": str(uuid.uuid4()), "credential": "x", "ledger_id": "bypass"},
    ],
)
def test_scan_api_rejects_malformed_contract(client, event, organizer, settings, payload):
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    response = client.post(
        reverse("scan-api", args=[event.slug]), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "REQUEST_ERROR"
    assert not CheckIn.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("decision", ["confirmed", "rejected", "cancelled"])
def test_later_verification_link_preserves_final_decision(client, event, decision):
    attendee = Attendee.objects.create(event=event, name="Legacy", email="legacy@example.invalid", notice_version="legacy")
    registration = Registration.objects.create(event=event, attendee=attendee, status=decision)
    token = new_action_token(attendee, "verify")
    response = client.post(reverse("ticket-access", args=[event.slug, token]))
    assert response.status_code == 410
    registration.refresh_from_db()
    assert registration.status == decision


@pytest.mark.django_db
def test_runbook_draft_audience_cannot_publish_private_content(client, event, organizer, settings):
    from operations.models import RunbookItem
    from core.workflows import action_resource

    settings.MFA_REQUIRED = False
    item = RunbookItem.objects.create(
        event=event, title="Private", instructions="Restricted cue", audience="leadership"
    )
    action_resource(event, organizer, "runbook", item.pk, "publish", "Approved restricted audience")
    item.refresh_from_db()
    item.audience = "staff"
    item.save()
    user = get_user_model().objects.create_user("staff-reader")
    RoleGrant.objects.create(event=event, user=user, role="volunteer", reason="Test")
    client.force_login(user)
    assert client.get(reverse("resource-detail", args=[event.slug, "runbook", item.pk])).status_code == 404


@pytest.mark.django_db
def test_missing_attendee_and_identity_mismatch_are_database_protected(event, organizer):
    ticket, _ = allocate(event, organizer)
    with pytest.raises(ProtectedError):
        ticket.attendee.delete()
    other = Attendee.objects.create(
        event=event, name="Other", email="other@example.invalid", notice_version="test-1"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("UPDATE admissions_ticket SET attendee_id=%s WHERE id=%s", [other.pk, ticket.pk])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.django_db(transaction=True)
def test_sixteen_concurrent_workers_with_database_delay(event, organizer):
    from threading import Barrier

    ticket, raw = allocate(event, organizer)
    event.entry_mode = "online"
    event.save()
    barrier = Barrier(16)

    def scan(index):
        try:
            barrier.wait(timeout=20)
            return check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"]
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=16) as pool:
        with transaction.atomic():
            Event.objects.select_for_update().get(pk=event.pk)
            futures = [pool.submit(scan, index) for index in range(16)]
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_sleep(0.3)")
        results = [future.result(timeout=30) for future in futures]
    assert results.count("VALID") == 1
    assert results.count("ALREADY_CHECKED_IN") == 15
    assert CheckIn.objects.filter(ticket=ticket).count() == 1


@pytest.mark.django_db
def test_expired_modified_and_unverified_credentials(event, organizer):
    ticket, raw = allocate(event, organizer)
    event.entry_mode = "online"
    event.save()
    assert (
        check_in(
            event, organizer, request_id=uuid.uuid4(), credential=raw[:-1] + ("A" if raw[-1] != "A" else "B")
        )["code"]
        == "INVALID"
    )
    ticket.expires_at = timezone.now() - timedelta(seconds=1)
    ticket.save()
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "EXPIRED"
    ticket.expires_at = event.ends_at
    ticket.save()
    ticket.attendee.verified_at = None
    ticket.attendee.save()
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "VALID"
    assert CheckIn.objects.count() == 1
