# Local development

## Prerequisites

Python 3.11, uv, PostgreSQL 15 or newer, and optionally Node 22 for rebuilding browser assets. The Windows helper uses `C:/Program Files/PostgreSQL/15/bin`; set `POSTGRES_BIN` for another installation. The repository has no established prior application stack to preserve.

Use the root commands in [platform/README.md](../../platform/README.md). The helper creates a separate cluster at `.local/pgdata`, bound only to `127.0.0.1:55432`. It does not change the existing Windows PostgreSQL service. It creates random local credentials in ignored `.env`. Do not print or commit that file. For an existing externally managed database, copy the example environment and configure it instead of running the helper.

`makemigrations` is for developers changing models; operators run committed `migrate` only. The custom database-boundary migration adds composite foreign keys and append-only triggers. It is intentionally not automatically reversible: recovery uses a reviewed forward migration or an isolated restore, not deletion of admission history.

## Accounts and event initialization

Import source-backed event settings and run `bootstrap_organizer username email`. The password prompt is hidden, validated, and not written to disk. No default admin password or bypass exists. First sign-in enrolls TOTP and displays one-use recovery codes. New accounts are invited through Team accounts; the organizer grants event roles separately. Acceptance of a volunteer application does not itself grant an account or permissions.

Local email defaults to the file backend under `.local/mail`; `deliver_notifications` writes messages there. These files contain private links and must not be shared or committed. Never use the real attendee roster in tests. Automated tests use `test_tedx` and `.invalid` email addresses. Tests exercise a separate live HTTP server and Chromium, with test-only fixture accounts.

## Routine commands

From `platform/`:

```powershell
../.venv/Scripts/python.exe manage.py check
../.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
../.venv/Scripts/python.exe -m ruff check .
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe manage.py collectstatic --noinput
```

The browser rehearsal requires Playwright Chromium installed. Screenshots go to ignored `.local/test-artifacts/` and contain synthetic identities only. Unit/integration tests use real PostgreSQL; SQLite is not a supported substitute for concurrency verification.

## Editing content and translations

Public pages are identified by key and language; edits remain drafts until an organizer publishes a snapshot. Speaker publication is separate from private contact/review data. English is the current interface baseline. Django i18n and RTL-aware layout are enabled; the event's public language list is configurable and still awaits the organizer's language/content decisions. Do not claim completed Turkish/Arabic translations without reviewed catalogs and content.
# Local one-click dashboard access

For an explicitly local development server, set `DEV_ONE_CLICK_LOGIN=true` and `DEV_LOGIN_EVENT=tedxgedik` in the private root `.env`, then restart the server bound to `127.0.0.1`. Open `/accounts/login/` and choose **Geliştirme için tek tıkla giriş**. This creates/reuses the passwordless `_tedx_local_developer` account with the existing event organizer role and records the login in the audit log. Existing staff credentials are unchanged.

The shortcut requires development mode, DEBUG, an explicit flag, a loopback peer and a localhost/loopback Host, with no forwarded-proxy headers. It uses a CSRF-protected POST. Only this marked local session bypasses MFA; normal accounts still require it. Turning the flag off and restarting invalidates these development sessions. Production startup refuses an enabled flag, and existing development sessions cannot survive a production/nonlocal transition. Keep `DEV_ONE_CLICK_LOGIN=false` in deployed environments.
# Local event rehearsal

Set `DEV_EVENT_REHEARSAL=true` only in the local `.env`, then run `python manage.py prepare_local_rehearsal` and restart the loopback-bound preview. The command reads the existing reviewed source file: 21 November 2026, public program 13:00–16:00, team access 12:00–17:00. It adopts the organizer-confirmed 12:45 admission time, opens free registration/general tickets and switches entry to Online. Existing attendees, tickets, consent history, venue/content edits and actual privacy approval are preserved. It refuses to invent privacy/policy approval or abandon an active manual reconciliation.

While enabled, the configured event skips registration-window, allocation-cutoff and admission-window waiting. Capacity, duplicate email, QR expiry/cancellation, authorization and atomic check-in still apply. The site displays a local-test banner and rejects non-loopback/proxied requests. Production startup refuses this flag. Auth/token expiry still uses actual time; this is not a global simulated clock. Test records remain in the local database, so use synthetic names and emails.

Before deployment set `DEV_EVENT_REHEARSAL=false` and `DEV_ONE_CLICK_LOGIN=false`; review publication/intake/entry mode, real doors time and privacy approvals using the normal launch checklist. Do not copy the development database to production as an attendee roster. The automated suite forces rehearsal off unless a test explicitly enables it.
