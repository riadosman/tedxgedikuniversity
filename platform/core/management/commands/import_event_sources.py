"""Import supported facts from the reviewed source map; never publish automatically."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Event, Page
from admissions.models import TicketType
from communications.models import NotificationTemplate


class Command(BaseCommand):
    help = (
        "Create the unpublished event from the existing discovery source map. Existing records are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(settings.ROOT_DIR / "docs/technology-discovery/01-event-facts-and-sources.md"),
        )
        parser.add_argument("--slug", default="tedxgedik")

    @transaction.atomic
    def handle(self, *args, **options):
        text = Path(options["source"]).read_text(encoding="utf-8")

        def fact(identifier):
            match = re.search(r"^\| " + identifier + r" \| (.*?) \|", text, re.M)
            if not match:
                raise CommandError(f"Missing source fact {identifier}; no data imported.")
            return match.group(1)

        def extracted(pattern: str, identifier: str, group: int = 0) -> str:
            match = re.search(pattern, fact(identifier))
            if match is None:
                raise CommandError(f"Source fact {identifier} has an unexpected format.")
            return match.group(group)

        name = extracted(r"`([^`]+)`", "F01", 1)
        date = datetime.strptime(fact("F02").split(";")[0], "%d %B %Y").date()
        capacity = int(extracted(r"\d+", "F03"))
        hours = re.findall(r"\d{2}:\d{2}", fact("F04"))
        if len(hours) != 4:
            raise CommandError("Source plan must contain audience and team start/end times.")

        def moment(value):
            return datetime.combine(
                date, datetime.strptime(value, "%H:%M").time(), ZoneInfo("Europe/Istanbul")
            )

        event, created = Event.objects.get_or_create(
            slug=options["slug"],
            defaults={
                "name": name,
                "starts_at": moment(hours[0]),
                "ends_at": moment(hours[1]),
                "setup_at": moment(hours[2]),
                "handover_at": moment(hours[3]),
                "licensed_capacity": capacity,
                "max_talk_minutes": int(extracted(r"\d+", "F10")),
                "source": "docs/technology-discovery/01-event-facts-and-sources.md F01–F04/F10; S01 licence correspondence, S05/S06 planned hours",
            },
        )
        if not created:
            if event.max_talk_minutes is None:
                event.max_talk_minutes = int(extracted(r"\d+", "F10"))
                event.save()
            self.stdout.write("Existing event preserved; no facts overwritten.")
        for key, title, body, source in [
            ("about", "About the event", fact("F08"), "F08; S04/S08"),
            ("theme", "Event theme", fact("F11"), "F11; proposed, requires approval"),
        ]:
            Page.objects.get_or_create(
                event=event, key=key, language="en", defaults={"title": title, "body": body, "source": source}
            )
        TicketType.objects.get_or_create(
            event=event, code="general", defaults={"name": "General admission", "enabled": False}
        )
        templates = {
            "schedule-update": (
                "Program update — {event}",
                "The approved program has been updated:\n\n{status}\n\nView the program: {link}",
            ),
            "attendee-invitation": (
                "Your invitation — {event}",
                "You are invited to apply for {event}.\n\nUse this private invitation link within 24 hours: {link}\n\nAn invitation is not a confirmed seat. Registration and capacity rules still apply.",
            ),
            "volunteer-access": (
                "Your volunteer application — {event}",
                "Hello {name},\n\nView or withdraw your application using this private link: {link}\n\nThe link expires in 30 minutes.",
            ),
            "registration-received": (
                "Verify your email for {event}",
                "Hello {name},\n\nVerify your email: {link}\n\nThis application is not a confirmed seat. The link expires in 30 minutes.",
            ),
            "registration-decision": (
                "Your registration update — {event}",
                "Hello {name},\n\nYour registration status is {status}.\nView your registration: {link}",
            ),
            "ticket-issued": (
                "Your ticket — {event}",
                "Hello {name},\n\nYour ticket: {ticket_id}\n{event_date}\n{venue}\n\nView and print your private QR ticket: {link}\n\nSave your ticket before the event.",
            ),
            "ticket-cancelled": (
                "Ticket cancelled — {event}",
                "Hello {name},\n\nYour ticket has been cancelled. It cannot be used for admission.\n{link}",
            ),
            "ticket-access": (
                "Your registration link — {event}",
                "Hello {name},\n\nYour ticket: {ticket_id}\n{event_date}\n{venue}\n\nView and print your ticket: {link}",
            ),
            "volunteer-decision": (
                "Volunteer application update — {event}",
                "Hello {name},\n\nYour volunteer application status is {status}. The team will contact you about any next steps.",
            ),
            "account-invitation": (
                "Your team account — {event}",
                "Hello {name},\n\nSet your password using this private link: {link}\n\nEvent access is assigned separately by the organizer.",
            ),
            "announcement": ("Event update — {event}", "Hello {name},\n\n{status}\n\n{link}"),
        }
        for key, (subject, body) in templates.items():
            NotificationTemplate.objects.get_or_create(
                event=event, key=key, language="en", defaults={"subject": subject, "body": body}
            )
        self.stdout.write(
            "Source-backed event and draft content imported. Publication, ticket type and registration remain disabled."
        )
