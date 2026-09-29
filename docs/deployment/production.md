# Production deployment and configuration

This is a deployment preparation guide, not evidence of a live deployment. Domain, hosting region, controller approval, transactional email account, file scanner, backup custody and operator assignments must be supplied before launch. Paid registration stays unavailable until its separate integration gate is complete.

## Environment variables

Copy [the environment example](../../platform/.env.example) to a private deployment secret store, not into the image.

| Variable | Purpose / production requirement |
|---|---|
| `DJANGO_ENV` | Must be `production`; enables secure cookies, HTTPS redirect and debug-off |
| `DJANGO_SECRET_KEY` | Random secret of at least 50 characters; separate from QR and backup keys |
| `DATABASE_URL` | PostgreSQL URL; use a dedicated runtime account and secret manager |
| `DB_SSLMODE` | Prefer `verify-full` with a trusted CA for a remote database; configure provider certificates |
| `CREDENTIAL_KEY` | Fernet key for QR delivery/outbox payloads; preserve through restore and rotate with a planned migration |
| `BACKUP_KEY` | Separate Fernet key for encrypted backups; keep an off-host recovery copy under named custody |
| `ALLOWED_HOSTS` | Comma-separated approved hostnames, without schemes |
| `PUBLIC_BASE_URL` | Exact HTTPS public origin; generated private links use this |
| `CSRF_TRUSTED_ORIGINS` | Approved HTTPS origins only |
| `TRUST_PROXY_HTTPS` | Defaults to `false`; enable only behind a controlled proxy that strips incoming `X-Forwarded-Proto` and supplies the actual scheme |
| `MFA_REQUIRED` | `true`; production refuses to start otherwise |
| `PRIVATE_MEDIA_ROOT` | Persistent private filesystem mount, outside static assets |
| `FILE_SCAN_COMMAND` | Fixed executable/arguments for malware scanning; receives a generated local path; exit 0 means clean. Without it uploads remain quarantined |
| `EMAIL_BACKEND` | Approved Django email backend; SMTP backend is supported; production rejects the file backend |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | Approved authenticated transactional mail configuration |
| `DEFAULT_FROM_EMAIL` | Verified event sender; mandatory in production |
| `EMAIL_FILE_PATH` | Development only; directory for private local email messages |
| `PAYMENT_PROVIDER` | Reserved selection boundary; setting it alone does not enable a provider |
| `LOG_LEVEL` | `INFO` for redacted request/job diagnostics |
| `POSTGRES_BIN` | Backup/local tooling executable directory on Windows |

## Build and release

Use `platform/` as the Docker build context. The Dockerfile installs the hashed production dependency lock and runs as UID 10001. Original event PDFs, email and artwork are outside the context. Mount persistent private storage with that account's permissions. No production dependency on Node is required; committed vendor assets are served locally.

1. Back up the database and files; verify the previous release is available.
2. Build the application image from the reviewed source. Supply secrets only at runtime.
3. Run `python manage.py migrate --noinput` once with the migration owner account.
4. Run `python manage.py check --deploy --fail-level WARNING` with real production environment settings.
5. Start the container behind a trusted HTTPS reverse proxy. `scripts/serve.sh` collects static files and starts Gunicorn. Do not use `runserver` in production.
6. Verify `/health/`, authentication, CSRF-protected POSTs, private downloads and ticket links on the real domain before exposing registration.

Terminate HTTPS at a controlled reverse proxy and prevent clients from reaching Gunicorn directly. Proxy-header trust must be explicitly configured for the chosen deployment; the default application does not trust arbitrary forwarded headers. If TLS terminates upstream, set `TRUST_PROXY_HTTPS=true` to enable `SECURE_PROXY_SSL_HEADER` only after the proxy strips client-supplied forwarded headers. Gunicorn's default trusted proxy IP is loopback. Container networking may require an explicit trusted proxy address.

Schedule `deliver_notifications --limit 50` every minute and `maintenance` periodically. Schedule daily encrypted backups; use provider-supported point-in-time recovery or a verified five-minute critical-window backup process to meet the discovery RPO target. `/health/` must be probed every 30 seconds by the chosen external monitor. Run `operations_health` to detect stale or failed mail. Monitoring setup and alert receipt require actual deployment evidence.

## Runtime database privilege separation

Migration owner creates schemas/functions. Runtime credentials must not be a superuser or table owner. Grant only required table operations and sequence access; revoke UPDATE/DELETE on `core_auditlog` and `admissions_checkin` in addition to their triggers. Do not expose database ports publicly. App RBAC cannot constrain a database superuser, backup operator or secret-store administrator.

## Rollback

Pause registration and admission, stop workers, and record outstanding scan requests. For a compatible code-only change, restart the previous image against the compatible schema. Do not reverse destructive migrations or restore over the live database casually. Restore into a new database, compare evidence, reapply later revocations/erasures and reconcile admission ledgers, then switch the connection under an approved recovery procedure. Keep entrance in manual/reconciling mode until the supervisor resolves uncertainty.
