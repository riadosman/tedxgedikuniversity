from django.core.management.base import BaseCommand
from communications.services import deliver_batch


class Command(BaseCommand):
    help = "Deliver queued transactional emails through the configured backend."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        from core.monitoring import heartbeat

        if not 1 <= options["limit"] <= 1000:
            from django.core.management.base import CommandError

            raise CommandError("Limit must be between 1 and 1000.")
        self.stdout.write(f"Accepted by backend: {deliver_batch(options['limit'])}")
        heartbeat("email")
