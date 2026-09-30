"""Read-only verification of the deployed registration prerequisites."""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.conf import settings
from core.models import Event, RoleGrant
from admissions.models import TicketType
from admissions.services import ensure_intake, allocation_allowed, committed


class Command(BaseCommand):
    help = "Check current ticket launch readiness without creating a registration."

    def add_arguments(self, parser):
        parser.add_argument("--event", default="tedxgedik")

    def handle(self, *args, **options):
        event = Event.objects.filter(slug=options["event"]).first()
        if event is None:
            raise CommandError("Import the event first: python manage.py import_event_sources")
        failures = []
        for check in (ensure_intake, allocation_allowed):
            try:
                check(event)
            except ValidationError as error:
                failures.extend(error.messages)
        if not TicketType.objects.filter(
            event=event, code="general", enabled=True, counts_capacity=True
        ).exists():
            failures.append("Enable the general ticket type with capacity counting.")
        if committed(event) >= event.capacity:
            failures.append("No remaining capacity.")
        if not RoleGrant.objects.filter(
            event=event, role="organizer", active=True, user__is_active=True
        ).exists():
            failures.append("Create an organizer with bootstrap_organizer.")
        if failures:
            raise CommandError("\n".join(str(item) for item in failures))
        self.stdout.write(self.style.SUCCESS("Registration prerequisites passed (no ticket created)."))
        for path in (
            "/",
            "/accounts/login/",
            "/staff/",
            f"/staff/{event.slug}/settings/",
            f"/e/{event.slug}/register/",
            f"/staff/{event.slug}/check-in/",
        ):
            self.stdout.write(settings.PUBLIC_BASE_URL + path)
        if not settings.OUTGOING_EMAIL_ENABLED or not event.ticket_email_enabled:
            self.stdout.write("Email is off: attendees must save/print the ticket shown after registration.")
