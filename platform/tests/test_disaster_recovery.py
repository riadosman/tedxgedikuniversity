"""Real PostgreSQL/file recovery using the documented retained-restore command boundary."""

import hashlib
import importlib.util
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import uuid
import pytest
import psycopg
from psycopg import sql
from cryptography.fernet import Fernet
from django.db import connection
from documents.models import Document
from admissions.services import check_in
from .test_admission import allocate


@pytest.mark.django_db(transaction=True)
def test_retained_database_file_and_secret_recovery(event, organizer, settings, monkeypatch, tmp_path):
    ticket, raw = allocate(event, organizer)
    event.entry_mode = "online"
    event.save()
    check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)
    media = tmp_path / "source"
    media.mkdir()
    content = b"%PDF-1.4\nSynthetic recovery fixture, not event content."
    (media / "fixture.pdf").write_bytes(content)
    Document.objects.create(
        event=event,
        title="Recovery fixture",
        original_name="fixture.pdf",
        storage_key="fixture.pdf",
        content_type="application/pdf",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        uploader=organizer,
    )
    parsed = urlparse(os.environ["DATABASE_URL"])
    monkeypatch.setenv(
        "DATABASE_URL", urlunparse(parsed._replace(path="/" + connection.settings_dict["NAME"]))
    )
    monkeypatch.setenv("PRIVATE_MEDIA_ROOT", str(media))
    spec = importlib.util.spec_from_file_location(
        "backup_rehearsal", Path(settings.BASE_DIR) / "scripts/backup.py"
    )
    assert spec and spec.loader
    backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup)
    archive = tmp_path / "recovery.enc"
    backup.backup(archive)
    backup.rehearse(archive)
    recovered = "tedx_recovery_" + uuid.uuid4().hex[:16]
    target = tmp_path / "restored"
    try:
        backup.rehearse(archive, keep_database=recovered, media_destination=str(target))
        assert (target / "fixture.pdf").read_bytes() == content
        with psycopg.connect(**{**backup.config(), "dbname": recovered}) as conn:
            assert (
                conn.execute(
                    "SELECT count(*) FROM admissions_checkin WHERE ticket_id=%s", [ticket.pk]
                ).fetchone()[0]
                == 1
            )
            encrypted = conn.execute(
                "SELECT ciphertext FROM admissions_credential WHERE ticket_id=%s AND revoked_at IS NULL",
                [ticket.pk],
            ).fetchone()[0]
            assert Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(encrypted.encode()).decode() == raw
        with pytest.raises(RuntimeError):
            backup.rehearse(archive, keep_database=recovered, media_destination=str(target))
    finally:
        assert recovered.startswith("tedx_recovery_") and recovered != backup.config()["dbname"]
        with psycopg.connect(**{**backup.config(), "dbname": "postgres"}, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(recovered)))
