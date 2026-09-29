"""Operator-only, fail-closed release of quarantined private uploads."""

import hashlib
import shlex
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.services import audit
from documents.models import Document


class Command(BaseCommand):
    help = "Scan quarantined uploads using FILE_SCAN_COMMAND; no scanner means no release."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        if not settings.FILE_SCAN_COMMAND:
            raise CommandError("Configure FILE_SCAN_COMMAND before releasing quarantined uploads.")
        if not 1 <= options["limit"] <= 100:
            raise CommandError("Limit must be between 1 and 100.")
        released = rejected = 0
        for document in Document.objects.filter(scan_status="quarantined", archived_at=None).order_by(
            "created_at"
        )[: options["limit"]]:
            path = (settings.MEDIA_ROOT / document.storage_key).resolve()
            if not path.is_relative_to(settings.MEDIA_ROOT.resolve()) or not path.is_file():
                continue
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            if before != document.sha256:
                status = "rejected"
            else:
                try:
                    result = subprocess.run(
                        [*shlex.split(settings.FILE_SCAN_COMMAND), str(path)], capture_output=True, timeout=60
                    )
                except (OSError, subprocess.TimeoutExpired):
                    continue  # Operational failures keep the upload quarantined.
                if result.returncode not in (0, 1):
                    continue  # Scanner errors are not a malware verdict; retry after repair.
                status = (
                    "clean"
                    if result.returncode == 0 and hashlib.sha256(path.read_bytes()).hexdigest() == before
                    else "rejected"
                )
            with transaction.atomic():
                locked = Document.objects.select_for_update().get(pk=document.pk)
                if locked.scan_status != "quarantined" or locked.archived_at:
                    continue
                locked.scan_status = status
                locked.save()
                audit(locked.event, None, "file.scan", locked, status=status, source="operator-command")
                released += status == "clean"
                rejected += status == "rejected"
        self.stdout.write(
            f"Released {released}; rejected {rejected}. Unavailable files/scanner failures remain quarantined."
        )
