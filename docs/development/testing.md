# Test and rehearsal procedures

Run from `platform/` after `npm ci --ignore-scripts`, installing the Python development lock and Playwright Chromium:

```powershell
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe -m ruff check .
../.venv/Scripts/python.exe manage.py check
../.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```

Tests use PostgreSQL's isolated `test_tedx` database and synthetic identities. No fixtures are loaded into the event database. `test_admission.py` covers ticket/credential transitions, wrong-event/malformed scans, idempotency and concurrency. `test_security_recovery.py` covers competing allocation, MFA replay, mixed-role scope, append-only audit, manual-ledger replay and retention holds. `test_complete_operations.py` rehearses volunteer/account/shift/program/runbook/incident/announcement workflows and private-file quarantine. `test_browser.py` uses a real browser and real HTTP/database endpoints; it deliberately drops one response after server commit to verify safe recovery. It also runs axe-core on selected core pages and checks mobile overflow.

The browser suite collects current static assets before running. Screenshots are stored under ignored `.local/test-artifacts/`. Test helpers can read the synthetic outbox to obtain private test links; those links must never be logged for real attendees.

For the deployment rehearsal, build `docker build -t tedxgedik-platform:local platform` from the workspace root, then run `.venv/Scripts/python.exe platform/scripts/container_rehearsal.py`. It creates random temporary credentials and an isolated Docker network/PostgreSQL container, applies migrations, checks production startup and headers, then removes its containers/network. It does not send email or touch the event database.

Run dependency audits against the committed locks. Record versions/date and any exclusions. The full acceptance matrix remains [discovery document 12](../technology-discovery/12-acceptance-and-testing.md); a passing automated test is only evidence for the behavior it actually exercises. Physical cameras, real SMTP deliverability, proxy/TLS configuration, actual venue load and manual assistive-technology checks need separate operating-environment evidence.

## Sustained service load

From `platform/`, set `$env:TEDX_LOAD_SECONDS="300"` and run `../.venv/Scripts/python.exe -m pytest tests/test_load.py -q`, then remove the variable with `Remove-Item Env:TEDX_LOAD_SECONDS`. The default suite uses a short version. Do not run two pytest processes against the same test database. The test targets 10 scan requests per second, checks one admission per ticket and writes latency evidence to `.local/test-artifacts/`. It measures the service/database boundary, not real HTTP, camera or venue-network latency.

`test_hardening.py` covers all non-organizer roles, cross-event denial, deactivated accounts, malformed/private uploads, scanner fail-closed behavior and configured ticket categories. The browser test also decodes a generated QR image with the locally shipped jsQR decoder; physical camera capture remains a separate rehearsal.
