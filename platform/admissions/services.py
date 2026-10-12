"""Ticket mutations lock the event; scans share that lock and lock their own ticket."""

from django.utils.translation import gettext_lazy as tr

import hashlib
import re
import secrets
import uuid
from datetime import timedelta, datetime
from django.contrib.auth.models import User, AnonymousUser
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import get_language
from core.models import Event
from core.permissions import require
from core.services import audit, locked_event
from core.dev_access import event_rehearsal
from communications.services import enqueue
from .models import (
    Attendee,
    Registration,
    TicketType,
    Ticket,
    Credential,
    ActionToken,
    CheckIn,
    ScanReceipt,
    NoticeVersion,
    Acknowledgement,
)

QR_PATTERN = re.compile(r"^tx2\.[A-Za-z0-9_-]{43}$")
LEGACY_QR_PATTERN = re.compile(r"^tx1\.([0-9a-f-]{36})\.([A-Za-z0-9_-]{43})$")
PHONE_PATTERN = re.compile(r"\+?[0-9 ()-]+")
PLATE_PATTERN = re.compile(r"[A-Za-z0-9 .-]+")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_phone(value: str) -> str:
    phone = " ".join(value.split())
    if not PHONE_PATTERN.fullmatch(phone) or not 10 <= sum(c.isdigit() for c in phone) <= 15:
        raise ValidationError(tr("Enter a phone number with 10–15 digits, for example +90 532 123 45 67."))
    return phone


def normalize_plate(value: str) -> str:
    """Group letters and digits the way plates are printed: 34abc123 → 34 ABC 123."""
    groups = re.findall(r"[A-Z]+|[0-9]+", value.strip().upper())
    if not PLATE_PATTERN.fullmatch(value.strip()) or not 2 <= len("".join(groups)) <= 12:
        raise ValidationError(tr("Enter the vehicle plate with letters and numbers, for example 34 ABC 123."))
    return " ".join(groups)


def ensure_intake(event: Event) -> None:
    now = timezone.now()
    if not event.published or event.registration_mode == "closed" or not event.policy_approved:
        raise ValidationError(tr("Registration is not open."))
    if not event_rehearsal(event) and (
        not event.opens_at or not event.closes_at or not event.opens_at <= now < event.closes_at
    ):
        raise ValidationError(tr("Registration is outside its opening period."))
    if not (event.privacy_approved and event.privacy_notice.strip() and event.notice_version.strip()):
        raise ValidationError(tr("Registration requires an approved KVKK information notice."))
    if event.payment_mode == "paid":
        from payments.providers import selected_provider

        selected_provider()
    if event.payment_mode != "free":
        raise ValidationError(tr("Admission policy is awaiting approval."))


def new_action_token(attendee: Attendee, purpose: str = "manage") -> str:
    raw = secrets.token_urlsafe(32)
    ActionToken.objects.create(
        event=attendee.event,
        attendee=attendee,
        digest=digest(raw),
        purpose=purpose,
        expires_at=max(timezone.now() + timedelta(minutes=30), attendee.event.ends_at + timedelta(days=1))
        if purpose == "manage"
        else timezone.now() + timedelta(minutes=30),
    )
    return raw


def notify_attendee(attendee: Attendee, key: str, status: str = "", purpose: str = "manage") -> None:
    raw = new_action_token(attendee, purpose)
    ticket = Ticket.objects.filter(attendee=attendee).first()
    enqueue(
        attendee.event,
        attendee.email,
        key,
        {
            "name": attendee.name,
            "status": status,
            "ticket_id": ticket.reference if ticket else "",
            "event_date": timezone.localtime(attendee.event.starts_at).isoformat(),
            "venue": attendee.event.venue,
            "link": f"{settings.PUBLIC_BASE_URL}/e/{attendee.event.slug}/access/{raw}/",
        },
        f"{key}:{uuid.uuid4()}",
    )


def normalize_email(email: str) -> str:
    # Existing event identity treats email case-insensitively; preserve dots and plus tags.
    from django.core.validators import validate_email

    email = email.strip().lower()
    validate_email(email)
    if len(email) > 254:
        raise ValidationError(tr("Enter a valid email address."))
    return email


def notice_digest(event: Event) -> str:
    return digest(event.privacy_notice)


def queue_ticket_email(attendee_id: uuid.UUID, key: str, status: str = "") -> None:
    """Called only after commit. Mail availability cannot roll back an issued ticket."""
    import logging

    try:
        attendee = Attendee.objects.select_related("event").get(pk=attendee_id)
        if attendee.event.ticket_email_enabled and getattr(settings, "OUTGOING_EMAIL_ENABLED", True):
            with transaction.atomic():
                notify_attendee(attendee, key, status)
    except Exception as error:
        logging.getLogger(__name__).warning("Ticket email queue failed: %s", type(error).__name__)


@transaction.atomic
def submit_registration(
    event: Event,
    *,
    name: str,
    email: str,
    privacy_acknowledged: bool = False,
    notice_version: str = "",
    notice_hash: str = "",
    phone: str = "",
    arrives_by_car: bool | None = None,
    vehicle_plate: str = "",
) -> Registration:
    event = locked_event(event)
    ensure_intake(event)
    allocation_allowed(event)
    name = name.strip()
    if not 1 <= len(name) <= 150 or any(ord(c) < 32 for c in name):
        raise ValidationError(tr("Enter a full name of 1–150 characters."))
    email = normalize_email(email)
    phone = normalize_phone(phone) if phone else ""
    vehicle_plate = normalize_plate(vehicle_plate) if arrives_by_car else ""
    if not privacy_acknowledged:
        raise ValidationError(tr("Acknowledge the KVKK information notice to register."))
    if notice_version != event.notice_version or notice_hash != notice_digest(event):
        raise ValidationError(
            tr("The information notice changed. Reload the form and read the current notice.")
        )
    if Attendee.objects.filter(event=event, email=email).exists():
        raise ValidationError(
            tr("This email is already registered for this event. No additional ticket was created.")
        )
    if not event.capacity or committed(event) >= event.capacity:
        raise ValidationError(tr("The event is full. No registration or ticket was created."))
    # The normal attendee flow never collects historical custom questions.
    notice, _ = NoticeVersion.objects.get_or_create(
        event=event, version_identifier=event.notice_version, defaults={"text": event.privacy_notice}
    )
    if notice.text != event.privacy_notice:
        raise ValidationError(tr("The notice text changed without a new version. Contact the organizer."))
    attendee = Attendee.objects.create(
        event=event,
        name=name,
        email=email,
        phone=phone,
        arrives_by_car=arrives_by_car,
        vehicle_plate=vehicle_plate,
        notice_version=notice.version_identifier,
        notification_language=get_language() if get_language() in event.enabled_languages else "en",
    )
    registration = Registration.objects.create(event=event, attendee=attendee, answers={})
    Acknowledgement.objects.create(event=event, attendee=attendee, notice=notice)
    _allocate(event, registration, None)
    audit(event, None, "registration.submitted", registration)
    return registration


def follow_event_end(event: Event, previous_end: datetime) -> int:
    """Tickets and manage links issued for the old event end stay valid until the new one."""
    moved = Ticket.objects.filter(event=event, expires_at=previous_end).update(expires_at=event.ends_at)
    ActionToken.objects.filter(
        event=event, purpose="manage", used_at__isnull=True, expires_at=previous_end + timedelta(days=1)
    ).update(expires_at=event.ends_at + timedelta(days=1))
    return moved


def committed(event: Event) -> int:
    return (
        Ticket.objects.filter(event=event, ticket_type__counts_capacity=True)
        .filter(Q(checkin__isnull=False) | Q(status__in=["registered", "checked_in"]))
        .count()
    )


def allocation_allowed(event: Event) -> None:
    if event.entry_mode in {"manual", "reconciling"}:
        raise ValidationError(tr("Ticket changes are frozen during manual admission and reconciliation."))
    cutoff = event.promotions_cutoff or event.setup_at or event.starts_at
    if not event_rehearsal(event) and timezone.now() >= cutoff:
        raise ValidationError(tr("Ticket allocation is closed for event-day admission."))


def create_credential(ticket: Ticket) -> Credential:
    raw = f"tx2.{secrets.token_urlsafe(32)}"
    return Credential.objects.create(
        event=ticket.event,
        ticket=ticket,
        digest=digest(raw),
        ciphertext=Fernet(settings.CREDENTIAL_KEY.encode()).encrypt(raw.encode()).decode(),
    )


def _allocate(
    event: Event, registration: Registration, actor: User | None, ticket_type: TicketType | None = None
) -> Ticket:
    allocation_allowed(event)
    if event.payment_mode != "free":
        raise ValidationError(tr("This allocation path requires approved free registration."))
    if Ticket.objects.filter(registration=registration).exists():
        raise ValidationError(tr("This registration already has a ticket. Use its lifecycle actions."))
    ticket_type = ticket_type or TicketType.objects.filter(event=event, code="general", enabled=True).first()
    if not ticket_type or ticket_type.event_id != event.pk or not ticket_type.enabled:
        raise ValidationError(tr("Configure an enabled admission ticket type first."))
    if not ticket_type.counts_capacity:
        raise ValidationError(
            tr("Non-counted ticket categories need a separately approved admission policy.")
        )
    if not event.capacity or committed(event) >= event.capacity:
        raise ValidationError(tr("The event is full. No registration or ticket was created."))
    ticket = Ticket.objects.create(
        event=event,
        attendee=registration.attendee,
        registration=registration,
        ticket_type=ticket_type,
        reference=secrets.token_hex(12).upper(),
        expires_at=event.ends_at,
    )
    create_credential(ticket)
    registration.status = "confirmed"
    registration.save()
    transaction.on_commit(lambda: queue_ticket_email(registration.attendee_id, "ticket-issued", "registered"))
    audit(event, actor, "ticket.issued", ticket)
    return ticket


@transaction.atomic
def cancel_ticket(
    event: Event,
    actor: User | None,
    ticket_id: uuid.UUID | str,
    reason: str,
    attendee: Attendee | None = None,
) -> Ticket:
    event = locked_event(event)
    if attendee is None:
        require(actor or AnonymousUser(), event, "tickets", "edit")
    ticket = Ticket.objects.select_for_update().get(event=event, pk=ticket_id)
    if attendee and attendee.pk != ticket.attendee_id:
        raise ValidationError(tr("Ticket does not belong to this attendee."))
    if not reason.strip():
        raise ValidationError(tr("Provide a cancellation reason."))
    if event.entry_mode in {"manual", "reconciling"}:
        raise ValidationError(tr("Ticket changes are frozen during manual admission."))
    if ticket.status == "cancelled":
        return ticket
    ticket.status = "cancelled"
    ticket.cancelled_at = timezone.now()
    ticket.save()
    Credential.objects.filter(ticket=ticket, revoked_at__isnull=True).update(revoked_at=timezone.now())
    registration = ticket.registration
    registration.status = "cancelled"
    registration.save()
    transaction.on_commit(lambda: queue_ticket_email(ticket.attendee_id, "ticket-cancelled", "cancelled"))
    audit(event, actor, "ticket.cancelled", ticket, reason=reason[:250])
    return ticket


@transaction.atomic
def rotate_ticket(event: Event, actor: User, ticket_id: uuid.UUID | str, reason: str) -> None:
    event = locked_event(event)
    require(actor or AnonymousUser(), event, "tickets", "edit")
    if event.entry_mode in {"manual", "reconciling"} or not reason.strip():
        raise ValidationError(tr("Rotation needs a reason and online operating mode."))
    ticket = Ticket.objects.select_for_update().get(
        event=event, pk=ticket_id, status__in=["registered", "checked_in"]
    )
    Credential.objects.filter(ticket=ticket, revoked_at__isnull=True).update(revoked_at=timezone.now())
    create_credential(ticket)
    transaction.on_commit(
        lambda: queue_ticket_email(ticket.attendee_id, "ticket-issued", "replacement credential")
    )
    audit(event, actor, "ticket.rotated", ticket, reason=reason[:250])


@transaction.atomic
def check_in(
    event: Event,
    actor: User,
    *,
    request_id: uuid.UUID | str,
    credential: str = "",
    ticket_id: uuid.UUID | str | None = None,
    reason: str = "",
    device: str = "",
    ledger_id: str | None = None,
    ledger_admitted_at: datetime | None = None,
) -> dict[str, str]:
    # Parallel desks may scan different tickets. A shared event lock still blocks
    # registration, cancellation, settings and entry-mode changes, all of which
    # take an exclusive event lock. Admission does not increase reserved capacity.
    # The individual ticket lock below serializes duplicate scans of one ticket.
    event = next(iter(Event.objects.raw("SELECT * FROM core_event WHERE id = %s FOR SHARE", [event.pk])))
    manual = ticket_id is not None
    require(actor, event, "manual-checkin" if manual else "checkin", "create")
    request_id = uuid.UUID(str(request_id))
    # A retried request can reach two workers before either receipt is committed.
    # Serialize only that request ID, preserving the same durable response while
    # allowing unrelated requests and entrance desks to proceed concurrently.
    request_lock = int.from_bytes(
        hashlib.sha256(f"scan-receipt:{event.pk}:{actor.pk}:{request_id}".encode()).digest()[:8],
        "big",
        signed=True,
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [request_lock])
    fingerprint = digest(f"{credential}|{ticket_id}|{reason}|{ledger_id}|{ledger_admitted_at}")
    if ledger_id:
        require(actor, event, "entry-mode", "approve")
        if (
            ledger_admitted_at is None
            or timezone.is_naive(ledger_admitted_at)
            or not (event.admission_opens_at or event.starts_at) <= ledger_admitted_at < event.ends_at
            or ledger_admitted_at > timezone.now()
        ):
            raise ValidationError(tr("A reconciled admission needs its actual, valid event-day timestamp."))
    existing = ScanReceipt.objects.filter(event=event, actor=actor, request_id=request_id).first()
    if existing:
        if existing.fingerprint != fingerprint:
            raise ValidationError(tr("A retry ID cannot be reused for a different request."))
        result = existing.result
        if not isinstance(result, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in result.items()
        ):
            raise ValidationError(tr("Invalid saved scan result."))
        result = dict(result)
        result["code"] = {"NEW_ADMISSION": "VALID", "ALREADY_ADMITTED": "ALREADY_CHECKED_IN"}.get(
            result.get("code", "INVALID"), result.get("code", "INVALID")
        )
        if result.get("code") in {"VALID", "ALREADY_CHECKED_IN"}:
            previous = (
                Ticket.objects.filter(event=event, reference=result.get("reference"))
                .select_related("attendee", "ticket_type")
                .first()
            )
            if previous:
                result.update(name=previous.attendee.name, ticket_type=previous.ticket_type.name)
        return result
    result = {"code": "INVALID", "receipt": str(request_id)}
    ticket = None
    if ledger_id and event.entry_mode != "reconciling":
        result["code"] = "RECONCILIATION_CLOSED"
    elif not ledger_id and event.entry_mode != "online":
        result["code"] = "ENTRY_PAUSED"
    elif (
        not ledger_id
        and not event_rehearsal(event)
        and not (event.admission_opens_at or event.starts_at) <= timezone.now() < event.ends_at
    ):
        result["code"] = "OUTSIDE_ENTRY_WINDOW"
    elif ticket_id is not None:
        if not reason.strip():
            raise ValidationError(tr("Manual admission requires a reason."))
        ticket = (
            Ticket.objects.select_for_update(of=("self",))
            .select_related("attendee", "ticket_type")
            .filter(event=event, pk=ticket_id)
            .first()
        )
    else:
        match = QR_PATTERN.fullmatch(credential)
        legacy = LEGACY_QR_PATTERN.fullmatch(credential)
        if legacy and legacy.group(1) != str(event.pk):
            result["code"] = "WRONG_EVENT"
        elif match or legacy:
            current = (
                Credential.objects.select_related("ticket")
                .filter(event=event, digest=digest(credential))
                .first()
            )
            if current and current.ticket.status == "cancelled":
                result["code"] = "CANCELLED"
            elif current and current.revoked_at is None:
                ticket = (
                    Ticket.objects.select_for_update(of=("self",))
                    .select_related("attendee", "ticket_type")
                    .get(pk=current.ticket_id, event=event)
                )
            elif current:
                result["code"] = "REVOKED"
    if ticket:
        if ticket.status not in {"registered", "checked_in"}:
            result["code"] = ticket.status.upper()
        elif not event.policy_approved:
            result["code"] = "POLICY_REVIEW_REQUIRED"
        elif (
            event.payment_mode == "paid"
            and getattr(getattr(ticket.registration, "order", None), "status", None) != "paid"
        ):
            result["code"] = "PAYMENT_REQUIRED"
        elif ticket.expires_at <= timezone.now() and not ledger_id:
            result["code"] = "EXPIRED"
        elif CheckIn.objects.filter(ticket=ticket).exists():
            result["code"] = "ALREADY_CHECKED_IN"
            result["admitted_at"] = ticket.checkin.admitted_at.isoformat()
        elif committed(event) > event.capacity:
            result["code"] = "CAPACITY_REVIEW_REQUIRED"
        else:
            record = CheckIn(
                event=event,
                ticket=ticket,
                actor=actor,
                admitted_at=ledger_admitted_at or timezone.now(),
                device=device[:80],
                source="reconciled" if ledger_id else "manual" if manual else "qr",
                reason=reason[:250],
                ledger_id=ledger_id,
            )
            # Event/ticket are already locked and actor authorization was checked.
            # Keep field/model validation; let the database enforce FK/uniqueness
            # instead of repeating SELECT checks while every entrance desk waits.
            record.full_clean(
                exclude={"event", "ticket", "actor"}, validate_unique=False, validate_constraints=False
            )
            CheckIn.objects.bulk_create([record])
            ticket.status = "checked_in"
            ticket.checked_in_at = record.admitted_at
            Ticket.objects.filter(pk=ticket.pk).update(
                status=ticket.status, checked_in_at=ticket.checked_in_at, updated_at=timezone.now()
            )
            result.update(code="VALID", admitted_at=record.admitted_at.isoformat())
            audit(event, actor, "checkin.created", record, source=record.source)
        if result["code"] in {"VALID", "ALREADY_CHECKED_IN"}:
            result.update(
                name=ticket.attendee.name, ticket_type=ticket.ticket_type.name, reference=ticket.reference
            )
    receipt = ScanReceipt(
        event=event,
        actor=actor,
        request_id=request_id,
        fingerprint=fingerprint,
        result={k: v for k, v in result.items() if k not in {"name", "ticket_type"}},
    )
    receipt.full_clean(exclude={"event", "actor"}, validate_unique=False, validate_constraints=False)
    ScanReceipt.objects.bulk_create([receipt])
    return result


@transaction.atomic
def set_entry_mode(event: Event, actor: User, mode: str, reason: str) -> None:
    event = locked_event(event)
    require(actor, event, "entry-mode", "approve")
    transitions = {
        "closed": {"online"},
        "online": {"manual", "closed"},
        "manual": {"reconciling"},
        "reconciling": {"online", "closed"},
    }
    if mode not in transitions[event.entry_mode] or not reason.strip():
        raise ValidationError(tr("Invalid entry-mode transition or missing reason."))
    if mode == "online" and (not event.policy_approved or not event.capacity or not event.admission_opens_at):
        raise ValidationError(
            tr("Approve event policy, capacity and entrance opening time before admitting guests.")
        )
    previous = event.entry_mode
    event.entry_mode = mode
    event.save()
    audit(event, actor, "entry.mode", event, previous=previous, current=mode, reason=reason[:250])
