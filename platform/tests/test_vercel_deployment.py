import json
import os
import subprocess
import sys

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO


@pytest.mark.django_db
def test_production_holding_page_renders_before_publication(client, settings):
    settings.DEBUG = False
    settings.PRODUCTION = True
    settings.LOCAL_EVENT_PREVIEW = False
    response = client.get("/")
    assert response.status_code == 200
    assert b"More information soon" in response.content
    assert "public/unpublished.html" in [template.name for template in response.templates]


def test_vercel_forces_production_and_supports_pooled_database(settings):
    env = {
        **os.environ,
        "VERCEL": "1",
        "VERCEL_URL": "preview-test.vercel.app",
        "VERCEL_BRANCH_URL": "branch-test.vercel.app",
        "VERCEL_PROJECT_PRODUCTION_URL": "tedxgedik.vercel.app",
        "DJANGO_ENV": "development",
        "DJANGO_SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql://user:pass@localhost/db?sslmode=require",
        "PUBLIC_BASE_URL": "https://test.vercel.app",
        "ALLOWED_HOSTS": "test.vercel.app",
        "CSRF_TRUSTED_ORIGINS": "https://test.vercel.app",
        "DEV_ONE_CLICK_LOGIN": "false",
        "DEV_EVENT_REHEARSAL": "false",
        "OUTGOING_EMAIL_ENABLED": "false",
        "MFA_REQUIRED": "true",
        "DB_SSLMODE": "require",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from config import settings as s; print(json.dumps([s.DEBUG, s.LOCAL_EVENT_PREVIEW, s.FILE_UPLOADS_ENABLED, s.DATABASES['default']['CONN_MAX_AGE'], s.DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'], s.DATABASES['default']['OPTIONS']['sslmode'], s.SECURE_PROXY_SSL_HEADER, s.ALLOWED_HOSTS]))",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert json.loads(result.stdout) == [
        False,
        False,
        False,
        0,
        True,
        "require",
        ["HTTP_X_FORWARDED_PROTO", "https"],
        ["test.vercel.app", "preview-test.vercel.app", "branch-test.vercel.app", "tedxgedik.vercel.app"],
    ]


@pytest.mark.django_db
def test_ticket_launch_checks_missing_organizer_and_closed_intake(event, organizer):
    output = StringIO()
    call_command("check_ticket_launch", event=event.slug, stdout=output)
    assert "prerequisites passed" in output.getvalue()
    event.registration_mode = "closed"
    event.save()
    with pytest.raises(CommandError, match="Registration is not open"):
        call_command("check_ticket_launch", event=event.slug)


@pytest.mark.django_db
def test_vercel_upload_does_not_write_ephemeral_file(client, organizer, event, settings):
    settings.MFA_REQUIRED = False
    settings.FILE_UPLOADS_ENABLED = False
    client.force_login(organizer)
    response = client.get(f"/staff/{event.slug}/files/new/")
    assert response.status_code == 503
    assert b"persistent storage" in response.content
