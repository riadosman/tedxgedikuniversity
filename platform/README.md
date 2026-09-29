# TEDxGedik event operations

Ticketing now uses immediate registration without mandatory email verification. See the [ticketing operating guide](../docs/operations/immediate-ticketing.md) and [printable guide](../output/ticket-review/operating-guide.pdf) for setup, migration, check-in and exports.

Django 5.2 LTS modular monolith with PostgreSQL, server-rendered public/staff interfaces, database-backed workflows and an authenticated mobile QR scanner. Original event documents stay outside the application build context.

Start with [local setup](../docs/development/local-setup.md), [architecture](../docs/architecture/platform.md), [operator guide](../docs/operations/admin-guide.md), and [implementation evidence](../docs/development/implementation-status.md). The discovery package is the historical requirements baseline; the organizer's full-platform implementation request supersedes its MVP sequencing and documentation-only restriction.

No event is automatically published. Registration, recruitment, admission hours, capacity and policy approval are explicit settings. No live payment provider is selected. Test identities exist only in pytest's isolated database.

```powershell
# From the workspace root, after installing Python/uv and PostgreSQL:
uv venv --python 3.11 .venv
uv pip sync --python .venv/Scripts/python.exe platform/requirements.lock
.venv/Scripts/python.exe platform/scripts/local_database.py
.venv/Scripts/python.exe platform/manage.py migrate
.venv/Scripts/python.exe platform/manage.py import_event_sources
.venv/Scripts/python.exe platform/manage.py bootstrap_organizer YOUR_USERNAME YOUR_EMAIL
.venv/Scripts/python.exe platform/manage.py runserver 127.0.0.1:8000
```

The initial password is entered through a hidden prompt. First sign-in requires authenticator enrollment. Keep the recovery codes private. Open `/staff/`; the public holding page is `/` until publication is approved.

From `platform/`, run `../.venv/Scripts/python.exe -m pytest -q`. Chromium browser tests require `../.venv/Scripts/python.exe -m playwright install chromium`. Run `npm ci --ignore-scripts` and `npm run vendor` only when rebuilding the pinned local QR decoder asset. Browsers do not load a third-party QR service.

Production review: [audit](../docs/development/production-readiness-audit.md), [release gates](../docs/development/production-readiness-checklist.md), [quality commands](../docs/development/code-quality.md), [organizer onboarding](../docs/operations/organizer-setup.md), and [event-day runbook](../docs/event-day/runbook.md).
