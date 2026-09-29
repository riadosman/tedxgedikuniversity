"""Boot the production image against a disposable PostgreSQL container, then clean up."""

import json
import secrets
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]


def run(*args, check=True):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError(f"Docker operation failed: {args[0]}. " + result.stderr[-1200:])
    return (result.stdout + (result.stderr if args[0] == "logs" else "")).strip()


def main():
    suffix = uuid.uuid4().hex[:10]
    network, database, application = [f"tedx-rehearsal-{part}-{suffix}" for part in ["net", "db", "app"]]
    password = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="container-rehearsal-", dir=ROOT / ".local") as temporary:
        private = Path(temporary)
        db_file = private / "database.env"
        app_file = private / "application.env"
        db_file.write_text(f"POSTGRES_USER=tedx_test\nPOSTGRES_DB=tedx_test\nPOSTGRES_PASSWORD={password}\n")
        app_file.write_text(
            "\n".join(
                [
                    "DJANGO_ENV=production",
                    "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(64),
                    "CREDENTIAL_KEY=" + Fernet.generate_key().decode(),
                    f"DATABASE_URL=postgresql://tedx_test:{password}@{database}:5432/tedx_test",
                    "PUBLIC_BASE_URL=https://rehearsal.example.invalid",
                    "ALLOWED_HOSTS=127.0.0.1,rehearsal.example.invalid",
                    "CSRF_TRUSTED_ORIGINS=https://rehearsal.example.invalid",
                    "MFA_REQUIRED=true",
                    "TRUST_PROXY_HTTPS=true",
                    "EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend",
                    "EMAIL_HOST=smtp.example.invalid",
                    "EMAIL_USE_TLS=true",
                    "DEFAULT_FROM_EMAIL=event@example.invalid",
                ]
            )
            + "\n"
        )
        run("network", "create", network)
        try:
            run(
                "run",
                "-d",
                "--name",
                database,
                "--network",
                network,
                "--env-file",
                str(db_file),
                "postgres:15-alpine",
            )
            for _ in range(60):
                ready = subprocess.run(
                    ["docker", "exec", database, "pg_isready", "-U", "tedx_test"], capture_output=True
                )
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Disposable PostgreSQL did not become ready.")
            print("Disposable PostgreSQL ready; applying production-image migrations.", flush=True)
            run(
                "run",
                "--rm",
                "--network",
                network,
                "--env-file",
                str(app_file),
                "tedxgedik-platform:local",
                "python",
                "manage.py",
                "migrate",
                "--noinput",
            )
            run(
                "run",
                "-d",
                "--name",
                application,
                "--network",
                network,
                "--env-file",
                str(app_file),
                "-p",
                "127.0.0.1::8000",
                "tedxgedik-platform:local",
            )
            port = run("port", application, "8000/tcp").rsplit(":", 1)[1]
            origin = f"http://127.0.0.1:{port}"
            for _ in range(45):
                try:
                    request = urllib.request.Request(
                        origin + "/health/", headers={"X-Forwarded-Proto": "https"}
                    )
                    with urllib.request.urlopen(request, timeout=3) as response:
                        if json.load(response)["status"] == "ok":
                            break
                except Exception:
                    time.sleep(1)
            else:
                raise RuntimeError(
                    "Production image did not become healthy: "
                    + run("logs", application, check=False)[-1200:]
                )
            for path in ["/", "/accounts/login/"]:
                with urllib.request.urlopen(
                    urllib.request.Request(origin + path, headers={"X-Forwarded-Proto": "https"}), timeout=5
                ) as response:
                    assert response.status == 200
                    assert response.headers["X-Frame-Options"] == "DENY"
                    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
                    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
            identity = run("exec", application, "id", "-u")
            assert identity == "10001"
            print(
                "Production-image rehearsal passed: migrations, non-root Gunicorn startup, PostgreSQL health, public/login pages and security headers. No external email sent.",
                flush=True,
            )
        finally:
            run("rm", "--force", "--volumes", application, database, check=False)
            run("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
