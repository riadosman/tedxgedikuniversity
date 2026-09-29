"""Loopback-only WSGI server behind the explicitly configured local tunnel."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402
from waitress import serve  # noqa: E402

if not settings.PRODUCTION or settings.DEBUG:
    raise RuntimeError("The public server requires the production configuration.")

serve(
    get_wsgi_application(),
    host="127.0.0.1",
    port=8011,
    threads=8,
    trusted_proxy="127.0.0.1",
    trusted_proxy_headers={"x-forwarded-proto"},
    max_request_body_size=30 * 1024 * 1024,
)
