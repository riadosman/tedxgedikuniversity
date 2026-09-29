from django.utils.translation import gettext_lazy as tr
import csv
import io
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from core.permissions import require
from core.services import locked_event, audit
from .models import ImportBatch, Ticket
from .services import digest, check_in
import uuid


@transaction.atomic
def preview_import(event, actor, content: bytes, kind: str):
    require(actor, event, "registrations", "edit")
    if len(content) > 1024 * 1024:
        raise ValidationError(tr("CSV files must be smaller than 1 MB."))
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        columns = (
            {"name", "email"}
            if kind == "registrations"
            else {"reference", "ledger_id", "admitted_at", "reason"}
        )
        if set(reader.fieldnames or []) != columns:
            raise ValidationError("CSV headers must be exactly: " + ", ".join(sorted(columns)))
        rows, seen = [], set()
        for index, data in enumerate(reader, 2):
            if index > 1001:
                raise ValidationError(tr("Import at most 1000 rows at a time."))
            if None in data or any(v is None or not v.strip() for v in data.values()):
                raise ValidationError(f"Row {index} has missing or extra values.")
            data = {k: v.strip() for k, v in data.items()}
            identity = data["email"].lower() if kind == "registrations" else data["ledger_id"]
            if identity in seen:
                raise ValidationError(f"Row {index} repeats an identity in this file.")
            seen.add(identity)
            if kind == "registrations":
                from django.core.validators import validate_email

                validate_email(data["email"])
                if len(data["name"]) > 150:
                    raise ValidationError(f"Row {index} has a name that is too long.")
            else:
                if len(data["ledger_id"]) > 100 or len(data["reason"]) > 250:
                    raise ValidationError(f"Row {index} exceeds field length limits.")
                moment = datetime.fromisoformat(data["admitted_at"])
                if (
                    timezone.is_naive(moment)
                    or not (event.admission_opens_at or event.starts_at) <= moment < event.ends_at
                    or moment > timezone.now()
                ):
                    raise ValidationError(
                        f"Row {index} must have a timezone-aware admission time within the event window."
                    )
                if not Ticket.objects.filter(event=event, reference=data["reference"]).exists():
                    raise ValidationError(
                        f"Row {index} has an unknown ticket. Resolve it with the supervisor first."
                    )
            rows.append(data)
        if not rows:
            raise ValidationError(tr("The file contains no records."))
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        raise ValidationError(tr("Use a valid UTF-8 CSV with ISO 8601 timestamps.")) from error
    batch, _ = ImportBatch.objects.get_or_create(
        event=event, digest=digest(kind + content.hex()), defaults={"rows": {"kind": kind, "items": rows}}
    )
    audit(event, actor, "import.preview", batch, kind=kind, rows=len(rows))
    return batch


@transaction.atomic
def commit_import(event, actor, batch_id, reason):
    event = locked_event(event)
    require(actor, event, "registrations", "edit")
    batch = ImportBatch.objects.select_for_update().get(event=event, pk=batch_id)
    if batch.committed_at:
        return batch
    if not reason.strip():
        raise ValidationError(tr("Record why this import is authorized."))
    kind, items = batch.rows["kind"], batch.rows["items"]
    if kind == "registrations":
        raise ValidationError(tr("Registration CSV import is retired. Attendees must acknowledge the current notice through the public registration form."))
    else:
        require(actor, event, "entry-mode", "approve")
        if event.entry_mode != "reconciling":
            raise ValidationError(tr("Switch to reconciliation mode before committing a manual ledger."))
        for data in items:
            ticket = Ticket.objects.get(event=event, reference=data["reference"])
            result = check_in(
                event,
                actor,
                request_id=uuid.uuid5(batch.pk, data["ledger_id"]),
                ticket_id=ticket.pk,
                reason=data["reason"],
                ledger_id=data["ledger_id"],
                ledger_admitted_at=datetime.fromisoformat(data["admitted_at"]),
            )
            if result["code"] not in {"VALID", "ALREADY_CHECKED_IN"}:
                raise ValidationError(f"Ledger row {data['ledger_id']} requires review: {result['code']}.")
    batch.committed_at = timezone.now()
    batch.save()
    audit(event, actor, "import.committed", batch, kind=kind, rows=len(items), reason=reason[:250])
    return batch
