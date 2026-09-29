"""Initialize an isolated local PostgreSQL cluster. Never touches another cluster."""

import os
import secrets
import shutil
import subprocess
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local"
DATA = LOCAL / "pgdata"


def main() -> None:
    LOCAL.mkdir(exist_ok=True)
    bin_dir = Path(os.environ.get("POSTGRES_BIN", "C:/Program Files/PostgreSQL/15/bin"))
    if not (bin_dir / "initdb.exe").exists() and os.name == "nt":
        raise SystemExit("Set POSTGRES_BIN to an installed PostgreSQL bin directory.")

    def run(name: str, *args: str) -> subprocess.CompletedProcess:
        executable = str(bin_dir / (name + ".exe")) if os.name == "nt" else shutil.which(name)
        return subprocess.run(
            [executable, *args],
            check=True,
            stdout=subprocess.DEVNULL if name == "pg_ctl" and "start" in args else subprocess.PIPE,
            stderr=subprocess.DEVNULL if name == "pg_ctl" and "start" in args else subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    if not DATA.exists():
        if (ROOT / ".env").exists():
            raise SystemExit(
                "Existing .env preserved. Configure database manually or use a separate workspace."
            )
        password = secrets.token_urlsafe(32)
        pwfile = LOCAL / "init-password"
        pwfile.write_text(password, encoding="ascii")
        try:
            run(
                "initdb",
                "-D",
                str(DATA),
                "-U",
                "tedx_owner",
                "-A",
                "scram-sha-256",
                "--pwfile",
                str(pwfile),
                "--encoding=UTF8",
                "--locale=C",
            )
        finally:
            pwfile.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a", encoding="utf-8") as file:
            file.write("\nlisten_addresses='127.0.0.1'\nport=55432\n")
        (ROOT / ".env").write_text(
            "DJANGO_ENV=development\nDJANGO_SECRET_KEY="
            + secrets.token_urlsafe(64)
            + "\nCREDENTIAL_KEY="
            + Fernet.generate_key().decode()
            + "\nDATABASE_URL=postgresql://tedx_owner:"
            + password
            + "@127.0.0.1:55432/tedx\n"
            "PUBLIC_BASE_URL=http://127.0.0.1:8000\nMFA_REQUIRED=true\n"
            "EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend\n"
            f"EMAIL_FILE_PATH={LOCAL / 'mail'}\nDEFAULT_FROM_EMAIL=local-test@example.invalid\n",
            encoding="utf-8",
        )
    try:
        run("pg_ctl", "-D", str(DATA), "status")
    except subprocess.CalledProcessError:
        run("pg_ctl", "-D", str(DATA), "-l", str(LOCAL / "postgres.log"), "start", "-w")
    from dotenv import dotenv_values
    import psycopg

    url = dotenv_values(ROOT / ".env")["DATABASE_URL"]
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.hostname != "127.0.0.1" or parsed.port != 55432 or parsed.path != "/tedx":
        raise SystemExit(
            "The environment no longer points to this isolated local cluster. No database changed."
        )
    with psycopg.connect(url.rsplit("/", 1)[0] + "/postgres", autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("tedx",)).fetchone():
            conn.execute("CREATE DATABASE tedx")
    print("Isolated local PostgreSQL ready on 127.0.0.1:55432. Credentials saved privately in .env.")


if __name__ == "__main__":
    main()
