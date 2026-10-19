"""Immediate ticketing acceptance tests; synthetic identities, isolated PostgreSQL."""

import csv
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections, transaction, DatabaseError
from django.urls import reverse

from admissions.models import Attendee, Ticket, Credential, CheckIn, Acknowledgement, NoticeVersion
from admissions.services import submit_registration, notice_digest, check_in, cancel_ticket, new_action_token
from communications.models import Notification, NotificationTemplate
from communications.services import deliver_batch
from core.models import Event, RoleGrant


def data(event, email="guest@example.invalid", **extra):
    return {
        "name": "Test Guest",
        "email": email,
        "phone": "+90 532 123 45 67",
        "gedik_student": "no",
        "arrives_by_car": "no",
        "privacy": "on",
        "notice_version": event.notice_version,
        "notice_hash": notice_digest(event),
        **extra,
    }


def register(event, email="guest@example.invalid", **extra):
    return submit_registration(
        event,
        name="Test Guest",
        email=email,
        privacy_acknowledged=True,
        notice_version=event.notice_version,
        notice_hash=notice_digest(event),
        **extra,
    )


def raw(ticket):
    return (
        Fernet(settings.CREDENTIAL_KEY.encode())
        .decrypt(ticket.credentials.get(revoked_at=None).ciphertext.encode())
        .decode()
    )


@pytest.mark.django_db
def test_registration_immediate_without_email(client, event, settings):
    settings.OUTGOING_EMAIL_ENABLED = False
    response = client.post(reverse("register", args=[event.slug]), data(event))
    assert response.status_code == 302
    ticket = Ticket.objects.get()
    assert ticket.status == "registered" and ticket.attendee.verified_at is None
    assert not Notification.objects.exists()
    page = client.get(response.url)
    assert page.status_code == 200 and ticket.reference.encode() in page.content
    assert b"Print ticket" in page.content
    assert str(ticket.pk).encode() not in page.content
    assert ticket.attendee.email.encode() not in page.content
    assert page["Cache-Control"] == "no-store, private" and page["Referrer-Policy"] == "strict-origin"
    qr = client.get(response.url + "qr/")
    assert qr.status_code == 200 and qr.content.startswith(b"\x89PNG")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad", [{"email": "bad"}, {"email": ""}, {"name": ""}, {"privacy": ""}, {"notice_hash": "stale"}]
)
def test_required_validation(client, event, bad):
    response = client.post(reverse("register", args=[event.slug]), data(event, **bad))
    assert response.status_code == 200
    assert not Attendee.objects.exists() and not Ticket.objects.exists()


@pytest.mark.django_db
def test_duplicate_does_not_disclose_existing_ticket(client, event):
    registration = register(event, email="Guest+Tag@Example.Invalid")
    response = client.post(
        reverse("register", args=[event.slug]), data(event, email=" guest+tag@example.invalid ")
    )
    assert b"already registered" in response.content
    assert registration.ticket.reference.encode() not in response.content
    assert raw(registration.ticket).encode() not in response.content
    assert Ticket.objects.count() == 1
    assert registration.attendee.email == "guest+tag@example.invalid"


@pytest.mark.django_db
def test_capacity_rolls_back_all_records(event):
    register(event)
    register(event, "two@example.invalid")
    with pytest.raises(ValidationError, match="full"):
        register(event, "three@example.invalid")
    assert Ticket.objects.count() == Attendee.objects.count() == Acknowledgement.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_registration_one_remaining(event):
    register(event)

    def attempt(index):
        try:
            register(Event.objects.get(pk=event.pk), f"concurrent{index}@example.invalid")
            return True
        except ValidationError:
            return False
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(8))) == 1
    assert Ticket.objects.count() == Attendee.objects.count() == 2


@pytest.mark.django_db
def test_tokens_are_secure_opaque_and_unique(event):
    event.capacity = 80
    event.save()
    import secrets

    with patch("admissions.services.secrets.token_urlsafe", wraps=secrets.token_urlsafe) as generator:
        tickets = [register(event, f"person{i}@example.invalid").ticket for i in range(32)]
    assert generator.call_count == 32
    assert all(call.args == (32,) for call in generator.call_args_list)
    tokens = [raw(ticket) for ticket in tickets]
    assert len(set(tokens)) == 32
    assert all(len(token) == 47 and token.startswith("tx2.") for token in tokens)
    assert all(str(event.pk) not in token and "@" not in token for token in tokens)
    assert len({ticket.reference for ticket in tickets}) == 32
    assert all(ticket.reference != str(ticket.pk) for ticket in tickets)


@pytest.mark.django_db
def test_acknowledgement_is_versioned_and_marketing_not_collected(client, event):
    response = client.get(reverse("register", args=[event.slug]))
    assert set(response.context["form"].fields) == {
        "name",
        "email",
        "phone",
        "gedik_student",
        "arrives_by_car",
        "vehicle_plate",
        "privacy",
        "notice_version",
        "notice_hash",
    }
    client.post(
        reverse("register", args=[event.slug]), data(event, marketing_consent="on", tc_kimlik="not-stored")
    )
    ack = Acknowledgement.objects.get()
    assert ack.kind == "privacy_notice_acknowledgement" and ack.created_at
    assert ack.notice.version_identifier == "test-1" and ack.notice.text == event.privacy_notice
    assert ack.attendee.registration.answers == {} and not ack.attendee.survey_consent
    event.notice_version = "test-2"
    event.privacy_notice = "Updated notice"
    event.save()
    register(event, "second@example.invalid")
    ack.refresh_from_db()
    assert ack.notice.text == "Test notice" and NoticeVersion.objects.count() == 2
    with pytest.raises(DatabaseError), transaction.atomic():
        Acknowledgement.objects.filter(pk=ack.pk).update(kind="marketing")
    with pytest.raises(DatabaseError), transaction.atomic():
        NoticeVersion.objects.filter(pk=ack.notice_id).update(text="Rewritten")


@pytest.mark.django_db
def test_unapproved_notice_closes_intake(client, event):
    event.privacy_approved = False
    event.save()
    response = client.post(reverse("register", args=[event.slug]), data(event))
    assert not Ticket.objects.exists() and b"approved KVKK" in response.content


@pytest.mark.django_db
def test_checkin_lifecycle_and_private_results(event, organizer):
    ticket = register(event).ticket
    event.entry_mode = "online"
    event.save()
    token = raw(ticket)
    first = check_in(event, organizer, request_id=uuid.uuid4(), credential=token)
    assert first["code"] == "VALID" and first["reference"] == ticket.reference
    duplicate = check_in(event, organizer, request_id=uuid.uuid4(), credential=token)
    assert duplicate["code"] == "ALREADY_CHECKED_IN" and duplicate["admitted_at"] == first["admitted_at"]
    ticket.refresh_from_db()
    assert ticket.status == "checked_in" and ticket.checked_in_at
    cancel_ticket(event, organizer, ticket.pk, "Test cancellation")
    cancelled = check_in(event, organizer, request_id=uuid.uuid4(), credential=token)
    assert cancelled["code"] == "CANCELLED" and "name" not in cancelled
    invalid = check_in(event, organizer, request_id=uuid.uuid4(), credential="tx2." + "A" * 43)
    assert invalid["code"] == "INVALID" and "name" not in invalid
    assert CheckIn.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_checkin_one_success(event, organizer):
    ticket = register(event).ticket
    event.entry_mode = "online"
    event.save()
    token = raw(ticket)

    def scan(_):
        try:
            return check_in(event, organizer, request_id=uuid.uuid4(), credential=token)["code"]
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(scan, range(2))) == ["ALREADY_CHECKED_IN", "VALID"]
    assert CheckIn.objects.count() == 1


@pytest.mark.django_db
def test_staff_search_export_authorization(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    ticket = register(event).ticket
    export = reverse("resource-export", args=[event.slug, "tickets"])
    scan = reverse("scan-api", args=[event.slug])
    assert client.post(scan, {}, content_type="application/json").status_code == 302
    assert client.post(export, {"reason": "Event administration"}).status_code == 302
    user = get_user_model().objects.create_user("desk")
    RoleGrant.objects.create(event=event, user=user, role="checkin", reason="Test")
    client.force_login(user)
    assert client.post(export, {"reason": "No permission"}).status_code == 403
    client.force_login(organizer)
    session = client.session
    from django.utils import timezone

    session["mfa_at"] = timezone.now().timestamp()
    session.save()
    for query in (ticket.reference, ticket.attendee.name, ticket.attendee.email):
        response = client.get(reverse("resource-list", args=[event.slug, "tickets"]), {"q": query})
        assert response.status_code == 200 and ticket.reference.encode() in response.content
    response = client.post(export, {"reason": "Event administration"})
    assert response.status_code == 200 and response["Content-Type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    assert rows[0] == [
        "name",
        "email",
        "phone",
        "arrives_by_car",
        "vehicle_plate",
        "gedik_student",
        "ticket_id",
        "ticket_status",
        "registered_at",
        "checked_in_at",
    ]
    assert ticket.attendee.email in rows[1] and raw(ticket) not in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_email_failure_cannot_invalidate_ticket(event, settings):
    event.ticket_email_enabled = True
    event.save()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    NotificationTemplate.objects.create(
        event=event,
        key="ticket-issued",
        subject="{event}",
        body="{name} {ticket_id} {event_date} {venue} {link}",
    )
    ticket = register(event).ticket
    assert Notification.objects.count() == 1
    with patch("communications.services.EmailMessage.send", side_effect=ConnectionError("Private SMTP text")):
        assert deliver_batch() == 0
    ticket.refresh_from_db()
    assert (
        ticket.status == "registered"
        and Credential.objects.filter(ticket=ticket, revoked_at=None).count() == 1
    )
    assert Notification.objects.get().last_error_code == "ConnectionError"
    with patch("admissions.services.notify_attendee", side_effect=ConnectionError("Private queue error")):
        assert register(event, "two@example.invalid").ticket.status == "registered"


@pytest.mark.django_db
def test_public_access_does_not_accept_reference_or_foreign_event(client, event):
    ticket = register(event).ticket
    response = client.get(reverse("ticket-access", args=[event.slug, ticket.reference]))
    assert response.status_code == 400 and ticket.attendee.name.encode() not in response.content
    response = client.get(reverse("ticket-qr", args=[event.slug, ticket.reference]))
    assert response.status_code == 404
    token = new_action_token(ticket.attendee)
    assert client.get(reverse("ticket-access", args=[event.slug, token])).status_code == 200


@pytest.mark.django_db
def test_authenticated_unassigned_user_cannot_scan(client, event, settings):
    settings.MFA_REQUIRED = False
    ticket = register(event).ticket
    user = get_user_model().objects.create_user("unassigned")
    client.force_login(user)
    response = client.post(
        reverse("scan-api", args=[event.slug]),
        {"request_id": str(uuid.uuid4()), "credential": raw(ticket)},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert not CheckIn.objects.exists()


@pytest.mark.django_db
def test_admin_correction_audited_and_old_links_revoked(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    ticket = register(event).ticket
    token = new_action_token(ticket.attendee)
    client.force_login(organizer)
    response = client.post(
        reverse("resource-edit", args=[event.slug, "attendees", ticket.attendee_id]),
        {
            "name": "Corrected guest",
            "email": "corrected@example.invalid",
            "version": ticket.attendee.version,
            "correction_reason": "Identity checked by organizer",
        },
    )
    assert response.status_code == 302
    ticket.attendee.refresh_from_db()
    assert ticket.attendee.email == "corrected@example.invalid"
    from core.models import AuditLog

    assert AuditLog.objects.filter(action="attendee.corrected", target=str(ticket.attendee_id)).exists()
    assert client.get(reverse("ticket-access", args=[event.slug, token])).status_code == 400
    assert Acknowledgement.objects.get().attendee_id == ticket.attendee_id


@pytest.mark.django_db
def test_survey_export_not_marketing_filtered(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    ticket = register(event).ticket
    event.entry_mode = "online"
    event.save()
    check_in(event, organizer, request_id=uuid.uuid4(), credential=raw(ticket))
    client.force_login(organizer)
    response = client.post(
        reverse("survey-export", args=[event.slug]), {"reason": "Approved post-event TEDx survey process"}
    )
    assert response.status_code == 200
    assert response.content.decode().splitlines() == ["email", ticket.attendee.email]
    assert not ticket.attendee.survey_consent


@pytest.mark.django_db
def test_legacy_qr_remains_valid(event, organizer):
    from admissions.services import digest

    ticket = register(event).ticket
    credential = ticket.credentials.get()
    legacy = f"tx1.{event.pk}." + "B" * 43
    credential.digest = digest(legacy)
    credential.ciphertext = Fernet(settings.CREDENTIAL_KEY.encode()).encrypt(legacy.encode()).decode()
    credential.save()
    event.entry_mode = "online"
    event.save()
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=legacy)["code"] == "VALID"


@pytest.mark.django_db
def test_throttling_and_csrf(event):
    from django.test import Client
    from core.models import RateBucket

    client = Client(enforce_csrf_checks=True)
    url = reverse("register", args=[event.slug])
    assert client.post(url, data(event)).status_code == 403
    client = Client()
    for index in range(4):
        client.post(url, data(event))
    assert RateBucket.objects.exists()
    assert Ticket.objects.count() == 1
    response = client.post(url, data(event))
    assert b"Too many" in response.content


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("conflicting_payload", [False, True])
def test_concurrent_scan_request_retry(event, organizer, conflicting_payload):
    from threading import Barrier
    from admissions.models import ScanReceipt

    first = register(event, email="retry-one@example.invalid").ticket
    second = register(event, email="retry-two@example.invalid").ticket if conflicting_payload else first
    credentials = [raw(first), raw(second)]
    event.entry_mode = "online"
    event.save()
    request_id = uuid.uuid4()
    ready = Barrier(2)

    def scan(credential):
        try:
            ready.wait(timeout=10)
            try:
                return check_in(event, organizer, request_id=request_id, credential=credential)
            except ValidationError:
                return {"code": "REQUEST_CONFLICT"}
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(scan, credentials))
    assert CheckIn.objects.filter(event=event).count() == 1
    assert ScanReceipt.objects.filter(event=event, request_id=request_id).count() == 1
    if conflicting_payload:
        assert sorted(result["code"] for result in results) == ["REQUEST_CONFLICT", "VALID"]
    else:
        assert results[0] == results[1]
        assert results[0]["code"] == "VALID"
