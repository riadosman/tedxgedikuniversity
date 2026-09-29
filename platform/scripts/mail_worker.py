"""Run the existing transactional outbox with fresh DB connections per cycle."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from communications.services import deliver_batch  # noqa: E402
from core.monitoring import heartbeat  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import close_old_connections  # noqa: E402
from django.core.management import call_command  # noqa: E402
from io import StringIO  # noqa: E402

if not settings.PRODUCTION or not settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"):
    raise RuntimeError("A production SMTP configuration is required.")

last_maintenance = 0.0
while True:
    try:
        close_old_connections()
        deliver_batch(limit=10)
        heartbeat("email")
        if time.monotonic() - last_maintenance > 3600:
            call_command("maintenance", stdout=StringIO())
            last_maintenance = time.monotonic()
    except Exception:
        # Do not log SMTP replies, recipient addresses, or private action links.
        print("Mail worker temporarily unavailable; retrying.", flush=True)
    time.sleep(5)
