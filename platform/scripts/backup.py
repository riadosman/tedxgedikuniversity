"""Encrypted backup + isolated restore verification. Never restore over an existing DB."""

import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlparse, unquote
import uuid
import zipfile
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def config():
    parsed = urlparse(os.environ["DATABASE_URL"])
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username),
        "password": unquote(parsed.password),
        "dbname": parsed.path.lstrip("/"),
        "sslmode": os.getenv("DB_SSLMODE", "prefer"),
    }


def pg_run(name, cfg, *arguments):
    folder = Path(os.getenv("POSTGRES_BIN", "C:/Program Files/PostgreSQL/15/bin"))
    executable = str(folder / (name + ".exe")) if os.name == "nt" else shutil.which(name)
    environment = os.environ.copy()
    environment.update(
        PGHOST=str(cfg["host"]),
        PGPORT=str(cfg["port"]),
        PGUSER=cfg["user"],
        PGPASSWORD=cfg["password"],
        PGDATABASE=cfg["dbname"],
        PGSSLMODE=cfg["sslmode"],
    )
    result = subprocess.run([executable, *arguments], env=environment, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"{name} failed (exit {result.returncode}); inspect configuration without exposing credentials."
        )


def table_counts(cfg):
    with psycopg.connect(**cfg) as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ).fetchall()
        return {
            table: conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[
                0
            ]
            for (table,) in tables
        }


def backup(destination):
    key = os.environ["BACKUP_KEY"].encode()
    cfg = config()
    destination = Path(destination).resolve()
    if destination.exists():
        raise RuntimeError("Backup destination already exists; choose a new file.")
    with tempfile.TemporaryDirectory(prefix="tedx-backup-") as temporary:
        dump = Path(temporary) / "database.dump"
        pg_run("pg_dump", cfg, "--format=custom", "--no-owner", "--no-privileges", "--file", str(dump))
        data = io.BytesIO()
        files = {}
        media = Path(os.getenv("PRIVATE_MEDIA_ROOT", str(ROOT / ".local/media"))).resolve()
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(dump, "database.dump")
            if media.exists():
                for path in media.rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        relative = "media/" + path.relative_to(media).as_posix()
                        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
                        archive.write(path, relative)
            archive.writestr(
                "manifest.json", json.dumps({"format": 1, "files": files, "counts": table_counts(cfg)})
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(Fernet(key).encrypt(data.getvalue()))
    print("Encrypted database/file backup created. Keep encryption keys outside backup storage.")


def rehearse(source, *, keep_database="", media_destination=""):
    started = time.monotonic()
    data = Fernet(os.environ["BACKUP_KEY"].encode()).decrypt(Path(source).read_bytes())
    cfg = config()
    if keep_database and (
        not re.fullmatch(r"tedx_recovery_[a-z0-9_]{1,40}", keep_database) or not media_destination
    ):
        raise RuntimeError(
            "Recovery requires a new tedx_recovery_* database and empty private media directory."
        )
    media_target = Path(media_destination).resolve() if media_destination else None
    if media_target and media_target.exists() and (not media_target.is_dir() or any(media_target.iterdir())):
        raise RuntimeError("Recovery media directory must be empty; nothing will be overwritten.")
    restore_name = keep_database or "tedx_restore_" + uuid.uuid4().hex[:16]
    completed = False
    restored = {**cfg, "dbname": restore_name}
    with psycopg.connect(**{**cfg, "dbname": "postgres"}, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restore_name)))
    try:
        with tempfile.TemporaryDirectory(prefix="tedx-restore-") as temporary:
            root = Path(temporary).resolve()
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    target = (root / member.filename).resolve()
                    if not target.is_relative_to(root):
                        raise RuntimeError("Unsafe archive path.")
                archive.extractall(root)
            manifest = json.loads((root / "manifest.json").read_text())
            for name, expected in manifest["files"].items():
                path = (root / name).resolve()
                if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise RuntimeError("Restored file checksum mismatch.")
            pg_run(
                "pg_restore",
                restored,
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                restore_name,
                str(root / "database.dump"),
            )
            if table_counts(restored) != manifest["counts"]:
                raise RuntimeError(
                    "Restored table counts differ. A live source may have changed during backup; quiesce and repeat."
                )
            with psycopg.connect(**restored) as conn:
                duplicates = conn.execute(
                    "SELECT ticket_id FROM admissions_checkin GROUP BY ticket_id HAVING count(*) > 1"
                ).fetchall()
                if duplicates:
                    raise RuntimeError("Restored admission invariant failed.")
            print(
                f"Restore verified: {len(manifest['counts'])} tables, {len(manifest['files'])} files; {time.monotonic() - started:.2f} seconds. Production database was not modified."
            )
            if media_target:
                media_target.mkdir(parents=True, exist_ok=True, mode=0o700)
                for name in manifest["files"]:
                    relative = Path(name).relative_to("media")
                    target = (media_target / relative).resolve()
                    if not target.is_relative_to(media_target):
                        raise RuntimeError("Unsafe media recovery path.")
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    shutil.copyfile(root / name, target)
                    target.chmod(0o600)
                print("Verified recovery retained. Connection cutover is a separate operator action.")
            completed = True
    finally:
        if not restore_name.startswith(("tedx_restore_", "tedx_recovery_")) or restore_name == cfg["dbname"]:
            raise RuntimeError("Refusing unsafe cleanup target.")
        if not keep_database or not completed:
            with psycopg.connect(**{**cfg, "dbname": "postgres"}, autocommit=True) as conn:
                conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(restore_name)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "rehearse", "restore"])
    parser.add_argument("path")
    parser.add_argument("--database", default="")
    parser.add_argument("--media-root", default="")
    arguments = parser.parse_args()
    if arguments.action == "restore":
        if not arguments.database or not arguments.media_root:
            parser.error("restore requires --database and --media-root")
        rehearse(arguments.path, keep_database=arguments.database, media_destination=arguments.media_root)
    else:
        (backup if arguments.action == "create" else rehearse)(arguments.path)
