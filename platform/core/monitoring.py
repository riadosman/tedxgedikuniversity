"""Redacted checks for a local scheduler or infrastructure monitoring agent."""

from datetime import timedelta
from pathlib import Path
import os
import shutil
import time
import json
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from communications.models import Notification
from admissions.models import ScanReceipt


def heartbeat(job: str) -> None:
    if job not in {"email", "maintenance"}:
        raise ValueError("Unknown job heartbeat.")
    folder = settings.MEDIA_ROOT / ".runtime"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = folder / f"{job}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps({"completed_at": time.time()}), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(folder / f"{job}.json")


def operational_health() -> dict[str, int | float | bool | str]:
    now = timezone.now()
    started = time.monotonic()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    latency = round((time.monotonic() - started) * 1000, 2)
    stale = Notification.objects.filter(
        Q(status="pending", next_attempt_at__lt=now - timedelta(minutes=5))
        | Q(status="sending", lease_until__lt=now)
    ).count()
    failed = Notification.objects.filter(status="failed").count()
    root = settings.MEDIA_ROOT.resolve()
    while not root.exists() and root != root.parent:
        root = root.parent
    free = shutil.disk_usage(root).free
    minimum = int(os.getenv("MIN_FREE_STORAGE_BYTES", str(1024**3)))
    rejected = (
        ScanReceipt.objects.filter(created_at__gte=now - timedelta(minutes=5))
        .exclude(result__code__in=["NEW_ADMISSION", "ALREADY_ADMITTED"])
        .count()
    )
    backup_dir = os.getenv("BACKUP_DIRECTORY", "")
    backups = list(Path(backup_dir).glob("*.enc")) if backup_dir else []
    backup_age = int(time.time() - max(path.stat().st_mtime for path in backups)) if backups else -1
    backup_ok = not backup_dir or 0 <= backup_age <= int(os.getenv("BACKUP_MAX_AGE_SECONDS", "90000"))
    jobs_ok = True
    job_ages: dict[str, int] = {}
    expected = os.getenv("EXPECT_BACKGROUND_JOBS", "true" if settings.PRODUCTION else "false") == "true"
    for job, maximum in [("email", 300), ("maintenance", 7200)]:
        path = settings.MEDIA_ROOT / ".runtime" / f"{job}.json"
        try:
            completed = json.loads(path.read_text(encoding="utf-8"))["completed_at"]
            age = int(time.time() - float(completed))
        except (OSError, ValueError, TypeError, KeyError):
            age = -1
        job_ages[f"{job}_heartbeat_age_seconds"] = age
        if expected and not 0 <= age <= maximum:
            jobs_ok = False
    return {
        "database_ms": latency,
        "stale_email_jobs": stale,
        "failed_email_jobs": failed,
        "storage_free_bytes": free,
        "storage_ok": free >= minimum,
        "rejected_scans_5m": rejected,
        "backup_age_seconds": backup_age,
        "backup_check_configured": bool(backup_dir),
        "backup_ok": backup_ok,
        **job_ages,
        "jobs_expected": expected,
        "jobs_ok": jobs_ok,
        "healthy": not (stale or failed) and free >= minimum and backup_ok and jobs_ok,
    }
