import json
from django.core.management.base import BaseCommand
from core.monitoring import operational_health


class Command(BaseCommand):
    help = "Print redacted operational health for monitoring; nonzero exit on stale delivery."

    def handle(self, *args, **options):
        try:
            result = operational_health()
        except Exception:
            result = {"healthy": False, "error": "health_check_failed"}
        self.stdout.write(json.dumps(result))
        if not result["healthy"]:
            raise SystemExit(1)
