from django.utils.translation import gettext_lazy as tr
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .permissions import require
from .models import PrivacyRequest
from .services import locked_event, audit


def erase_attendee(event, attendee, now):
    """Remove an attendee's personal data and access; anonymous rows stay for capacity and audit history."""
    from admissions.models import Registration, Credential, ActionToken, ScanReceipt, Ticket

    Credential.objects.filter(ticket__attendee=attendee).update(ciphertext="", revoked_at=now)
    ActionToken.objects.filter(attendee=attendee).delete()
    Registration.objects.filter(attendee=attendee).update(answers={}, decision_note="")
    attendee.name, attendee.email, attendee.survey_consent, attendee.anonymized_at = (
        "Anonymized attendee",
        None,
        False,
        now,
    )
    attendee.phone, attendee.arrives_by_car, attendee.vehicle_plate = "", None, ""
    attendee.gedik_student = None
    attendee.save()
    references = Ticket.objects.filter(attendee=attendee).values_list("reference", flat=True)
    for receipt in ScanReceipt.objects.filter(event=event, result__reference__in=list(references)):
        receipt.result = {k: v for k, v in receipt.result.items() if k not in {"name", "ticket_type"}}
        receipt.save()


@transaction.atomic
def delete_registration(event, actor, attendee_id, reason):
    """Staff deletion: cancel the ticket, free the seat and erase personal data immediately.

    Rows are not removed: the consent record, audit log and capacity history keep pointing at the
    anonymous attendee. Admitted attendees stay in the admission history and cannot be deleted.
    """
    from admissions.models import Attendee, CheckIn, Registration, Ticket
    from communications.models import Notification

    event = locked_event(event)
    require(actor, event, "attendees", "edit")
    if not reason.strip():
        raise ValidationError(tr("Record the reason for deleting this registration."))
    if event.entry_mode in {"manual", "reconciling"}:
        raise ValidationError(tr("Ticket changes are frozen during manual admission."))
    attendee = Attendee.objects.select_for_update().get(
        event=event, pk=attendee_id, anonymized_at__isnull=True
    )
    ticket = Ticket.objects.select_for_update().filter(attendee=attendee).first()
    if ticket and (ticket.status == "checked_in" or CheckIn.objects.filter(ticket=ticket).exists()):
        raise ValidationError(
            tr("An admitted attendee cannot be deleted; the admission stays in the history.")
        )
    now = timezone.now()
    if ticket and ticket.status != "cancelled":
        ticket.status, ticket.cancelled_at = "cancelled", now
        ticket.save()
    Registration.objects.filter(attendee=attendee).update(status="cancelled")
    if attendee.email:
        Notification.objects.filter(event=event, recipient=attendee.email).update(
            recipient="anonymized@example.invalid", payload_ciphertext="", status="suppressed"
        )
    erase_attendee(event, attendee, now)
    audit(event, actor, "registration.deleted", attendee, reason=reason[:250])
    return attendee


@transaction.atomic
def anonymize_attendee(event, actor, request_id, reason):
    event = locked_event(event)
    require(actor, event, "privacy", "approve")
    item = PrivacyRequest.objects.select_for_update().get(event=event, pk=request_id)
    if item.status != "verified" or item.kind != "erase" or not reason.strip():
        raise ValidationError(tr("An erasure needs a verified request and an approval reason."))
    now = timezone.now()
    if item.hold_until and item.hold_until > now:
        raise ValidationError(tr("A documented retention hold is still active."))
    if event.retention_days is None or not event.retention_reason.strip():
        raise ValidationError(
            tr(
                "Configure and document the retention policy before erasure, including TEDx survey and legal/audit needs."
            )
        )
    if event.ends_at + timedelta(days=event.retention_days) > now:
        raise ValidationError(
            tr("The configured event retention period has not elapsed. Resolve policy before erasure.")
        )
    from admissions.models import Attendee
    from communications.models import Notification
    from team.models import Volunteer, VolunteerApplication
    from django.contrib.auth import get_user_model

    attendee = Attendee.objects.filter(event=event, email=item.email.lower()).first()
    if attendee:
        erase_attendee(event, attendee, now)
    volunteers = Volunteer.objects.filter(event=event, email=item.email.lower())
    user_ids = list(volunteers.exclude(user=None).values_list("user_id", flat=True))
    volunteers.update(
        name="Anonymized volunteer",
        email=f"erased-{item.pk}@example.invalid",
        skills="",
        languages="",
        availability="",
        active=False,
    )
    VolunteerApplication.objects.filter(event=event, email=item.email.lower()).update(
        name="Anonymized applicant",
        skills="",
        languages="",
        availability="",
        internal_notes="",
        email=f"erased-{item.pk}@example.invalid",
    )
    from .models import RoleGrant

    RoleGrant.objects.filter(event=event, user_id__in=user_ids, role="volunteer").update(active=False)
    # Accounts may serve other events/roles; event erasure must not disable those identities.
    remaining = RoleGrant.objects.filter(user_id__in=user_ids, active=True).values_list("user_id", flat=True)
    get_user_model().objects.filter(pk__in=user_ids).exclude(pk__in=remaining).update(is_active=False)
    Notification.objects.filter(event=event, recipient=item.email.lower()).update(
        recipient="anonymized@example.invalid", payload_ciphertext="", status="suppressed"
    )
    item.email = f"erased-{item.pk}@example.invalid"
    item.status, item.resolution = "resolved", reason[:250]
    item.save()
    audit(
        event,
        actor,
        "privacy.anonymized",
        item,
        attendee_id=str(attendee.pk) if attendee else "",
        reason=reason[:250],
    )
    return item
