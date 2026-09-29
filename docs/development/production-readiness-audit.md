# Production readiness audit

17 September 2026. Existing modules were inspected and hardened, not rebuilt or reduced. Functional software status is separate from real deployment/venue readiness. Final release evidence is in the [checklist](production-readiness-checklist.md).

| Module | Classification | Inspected implementation / boundary |
|---|---|---|
| Authentication/MFA | Complete but needs hardening | core/auth_views.py, middleware, Django auth; real passwords/TOTP/recovery/replay/session controls; account custody external |
| Authorization/RBAC | Complete but needs hardening | permissions.py/forms.py/workflows.py; event/department/owner scopes and regression tests |
| Database | Complete but needs hardening | model/migration FKs, composite event identities, enum checks, immutable history; deployed runtime grants external |
| Registration | Complete | verified lifecycle, custom fields, waitlist/decisions and late-token regression |
| Tickets/QR | Complete | random event-scoped credentials, encrypted delivery, expiry/rotation/cancellation; free model tested |
| Check-in/APIs | Complete but needs hardening | validated request contract, transactions, unique admission and durable retry; physical environment untested |
| Volunteers/departments | Complete | acceptance separate from privileges, memberships, shifts and workflow rehearsal |
| Tasks | Complete | owner/scope/dependency/cycle/review/deadline/comment behavior |
| Speakers/schedules | Complete | public/private snapshots, readiness/release/rights, approval, overlap/duration checks |
| Incidents/announcements | Complete | scoped reporting/resolution; targeted approval/scheduling/read state |
| Runbook | Complete | snapshot audience isolation, approval and acknowledgments; legacy unscoped snapshots require republication |
| Files | Complete but needs hardening | private paths, signatures/image/archive limits, quarantine, authorization; real scanner external |
| Notifications/background jobs | Complete but needs hardening | encrypted leases/retries, language selection and heartbeat checks; provider evidence external |
| Email | Partially complete | adapter/templates exist; real sender/DNS/inbox evidence absent |
| Reports | Complete | DB aggregates, purpose-audited scoped CSV, formula defense; physical reconciliation external |
| Audit logs | Complete | append-only application/database controls; database owner remains trusted infrastructure |
| CMS/public website | Complete but needs hardening | focused page/speaker/program snapshots, escaped templates/catalogs; approved content/branding external |
| Admin interface | Complete but needs hardening | distinct authorized modules, scoped fields and stale-edit handling; staff rehearsal external |
| Backups | Complete but needs hardening | encrypted dump/files, disposable/retained new-database restore; off-host custody/RPO/RTO external |
| Deployment | Complete but needs hardening | non-root Gunicorn/migrations/settings/container rehearsal; real hosting unconfigured |
| Payments | Missing (conditional) | typed boundary fails closed; no provider/business approval or working payment integration claimed |

## Security review

Reviewed object/field authorization, mixed roles, snapshots, mutation routes, CSRF, escaping, redirects, ORM/SQL, upload/download paths, session/MFA/password protection, settings, credentials/replay/concurrency, private data, jobs and backups. ORM queries parameterize user input. Recovery/schema SQL uses trusted/quoted identifiers. Django auth/i18n keep framework redirect-host checks. There is no unverified payment webhook endpoint.

Fixes include late verification resetting decisions, malformed scanner payloads/edit versions, last-organizer expiry, cross-event global-account deactivation, verified-address mutation, runbook draft audience disclosure, stronger upload validation/permissions, localized mail and conditional worker result writes, future mail falsely considered overdue, missing heartbeats/storage/backup observability, unsafe production mail fallbacks, broad default HSTS scope and inaccessible timed refresh. Critical changes have regression tests.

Initial 38 tests were rerun successfully. Repeated five-minute service load: 3,000 requests, 100 first admissions, zero duplicates; local p95 166.25 ms/p99 253.63 ms excluding HTTP/device/network. Additional 16-worker contention injects database lock delay. Final post-change checks are recorded separately after changes settle.

No university approval, paid checkout, real SMTP delivery, malware-engine result, physical camera support, WCAG certification or off-host recovery is inferred from local tests. Reference checks: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) and [mypy migration guidance](https://mypy.readthedocs.io/en/stable/existing_code.html).

## Final evidence and remaining developer scope

58 tests passed; Ruff and configured mypy checks passed. Admission/permission/core service boundaries now have strict annotations. Final image startup and encrypted retained recovery passed. Original 41 source-file hashes remain unchanged. Additional fixes cover exception-traceback redaction, restored-heartbeat freshness, scanner error-code quarantine and missing admission-history export. See the checklist for the distinction between local PASS and actual deployment/staff gates.

Full repository-wide strict typing and exhaustive dynamic-string localization remain incomplete developer work. They are explicitly FAIL gates, not disguised as external configuration blockers. All current extracted catalog entries have translations, but that does not prove dynamic runtime coverage. No full WCAG or production-ready claim is made.
