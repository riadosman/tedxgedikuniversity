"""Prepare the existing local event from its reviewed source plan, preserving records."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Event
from core.services import audit
from admissions.models import TicketType


class Command(BaseCommand):
    help = "Apply documented event hours and open the explicit local rehearsal; never legal approvals."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.PRODUCTION or not settings.DEBUG or not settings.DEV_EVENT_REHEARSAL:
            raise CommandError("Enable DEV_EVENT_REHEARSAL only in local development first.")
        text = (
            Path(settings.ROOT_DIR) / "docs/technology-discovery/01-event-facts-and-sources.md"
        ).read_text(encoding="utf-8")

        def fact(key):
            match = re.search(r"^\| " + key + r" \| (.*?) \|", text, re.M)
            if not match:
                raise CommandError(f"Missing source fact {key}")
            return match.group(1)

        date = datetime.strptime(fact("F02").split(";")[0], "%d %B %Y").date()
        hours = re.findall(r"\d{2}:\d{2}", fact("F04"))
        door = re.search(r"suggests (\d{2}:\d{2}) admission", fact("C04"))
        if len(hours) != 4 or not door:
            raise CommandError("The source plan does not contain the expected hours.")

        def moment(value):
            return datetime.combine(
                date, datetime.strptime(value, "%H:%M").time(), ZoneInfo("Europe/Istanbul")
            )

        event = Event.objects.select_for_update().get(slug=settings.DEV_LOGIN_EVENT)
        if not (event.privacy_approved and event.privacy_notice.strip() and event.notice_version.strip()):
            raise CommandError(
                "An existing approved notice is required; rehearsal never fabricates approval."
            )
        if event.entry_mode in {"manual", "reconciling"}:
            raise CommandError("Complete existing entrance reconciliation before preparing a rehearsal.")
        if not event.policy_approved:
            raise CommandError("The existing admission policy must be approved first.")
        event.starts_at, event.ends_at = moment(hours[0]), moment(hours[1])
        event.setup_at, event.handover_at = moment(hours[2]), moment(hours[3])
        event.admission_opens_at = moment(door.group(1))
        event.capacity = event.capacity or event.licensed_capacity
        event.payment_mode = "free"
        event.registration_mode = "first_come"
        event.entry_mode = "online"
        event.opens_at = event.opens_at or timezone.now() - timedelta(days=1)
        event.closes_at = event.closes_at or event.starts_at
        event.published = True
        event.version += 1
        event.save()
        category, _ = TicketType.objects.get_or_create(
            event=event, code="general", defaults={"name": "General admission"}
        )
        category.enabled = True
        category.save()
        audit(
            event,
            None,
            "event.local_rehearsal_prepared",
            event,
            source="F02/F04; C04 proposed doors adopted for local test only",
        )
        self.stdout.write(
            "Local rehearsal ready. Source dates preserved; registration and QR entrance online. Existing tickets and privacy approvals preserved. C04 doors time is a test default, not venue approval."
        )
