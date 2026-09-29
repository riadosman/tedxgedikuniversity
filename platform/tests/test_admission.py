import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections
from admissions.models import Attendee, Ticket, CheckIn
from admissions.services import submit_registration, notice_digest, check_in, cancel_ticket, committed, rotate_ticket
from core.models import Event


def allocate(event, actor, email="person@example.invalid"):
    registration = submit_registration(event, name="Test attendee", email=email,
        privacy_acknowledged=True, notice_version=event.notice_version, notice_hash=notice_digest(event))
    ticket = Ticket.objects.get(registration=registration)
    raw = (
        Fernet(settings.CREDENTIAL_KEY.encode())
        .decrypt(ticket.credentials.get(revoked_at=None).ciphertext.encode())
        .decode()
    )
    return ticket, raw


@pytest.mark.django_db
def test_ticket_checkin_lifecycle(event, organizer):
    ticket, raw = allocate(event, organizer)
    event.entry_mode = "online"
    event.save()
    rid = uuid.uuid4()
    a = check_in(event, organizer, request_id=rid, credential=raw)
    assert a["code"] == "VALID"
    assert check_in(event, organizer, request_id=rid, credential=raw) == a
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "ALREADY_CHECKED_IN"
    rotate_ticket(event, organizer, ticket.pk, "Compromised credential")
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "REVOKED"
    cancel_ticket(event, organizer, ticket.pk, "Cancelled after entry")
    assert committed(event) == 1
    assert CheckIn.objects.filter(ticket=ticket).count() == 1


@pytest.mark.django_db
def test_capacity_waitlist(event, organizer):
    allocate(event, organizer)
    allocate(event, organizer, "two@example.invalid")
    with pytest.raises(ValidationError, match="full"):
        allocate(event, organizer, "three@example.invalid")
    assert Ticket.objects.filter(event=event).count() == 2
    assert Attendee.objects.filter(event=event).count() == 2


@pytest.mark.django_db
def test_wrong_event_invalid_paused_and_unauthorized(event, organizer):
    ticket, raw = allocate(event, organizer)
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "ENTRY_PAUSED"
    event.entry_mode = "online"
    event.save()
    wrong = f"tx1.{uuid.uuid4()}." + "A" * 43
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=wrong)["code"] == "WRONG_EVENT"
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential="garbage")["code"] == "INVALID"
    organizer.is_active = False
    organizer.save()
    with pytest.raises(PermissionDenied):
        check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)


@pytest.mark.django_db(transaction=True)
def test_simultaneous_scans_have_one_winner(event, organizer):
    _, raw = allocate(event, organizer)
    event.entry_mode = "online"
    event.save()

    def scan(_):
        try:
            return check_in(
                Event.objects.get(pk=event.pk), organizer, request_id=uuid.uuid4(), credential=raw
            )["code"]
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(scan, range(2)))
    assert sorted(results) == ["ALREADY_CHECKED_IN", "VALID"]
    assert CheckIn.objects.count() == 1


@pytest.mark.django_db
def test_receipt_cannot_change_input(event, organizer):
    _, raw = allocate(event, organizer)
    rid = uuid.uuid4()
    check_in(event, organizer, request_id=rid, credential=raw)
    with pytest.raises(ValidationError):
        check_in(event, organizer, request_id=rid, credential="different")


@pytest.mark.django_db
def test_cross_event_database_constraint(event, organizer):
    ticket, _ = allocate(event, organizer)
    with pytest.raises(Exception):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE admissions_ticket SET event_id = %s WHERE id = %s", [uuid.uuid4(), ticket.pk]
            )
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
