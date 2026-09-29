from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import Event, RateBucket
from core.services import audit
from admissions.models import Ticket, Credential, ActionToken


class Command(BaseCommand):
    help = (
        "Expire ended tickets and short-lived action tokens. Never erases attendee identities automatically."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        RateBucket.objects.filter(expires_at__lt=now).delete()
        ActionToken.objects.filter(expires_at__lt=now).delete()
        total = 0
        for event_id in Event.objects.values_list("pk", flat=True):
            with transaction.atomic():
                event = Event.objects.select_for_update().get(pk=event_id)
                if event.entry_mode in {"manual", "reconciling"}:
                    continue
                tickets = Ticket.objects.filter(event=event, status="registered", expires_at__lte=now)
                count = tickets.count()
                Credential.objects.filter(ticket__in=tickets, revoked_at__isnull=True).update(revoked_at=now)
                tickets.update(status="expired")
                if count:
                    audit(event, None, "tickets.expired", event, count=count)
                if event.ends_at + timedelta(days=30) < now:
                    Credential.objects.filter(event=event).update(ciphertext="", revoked_at=now)
                total += count
        self.stdout.write(
            f"Expired tickets: {total}. Retention erasure remains an approved separate workflow."
        )
        from core.monitoring import heartbeat

        heartbeat("maintenance")
