# Production readiness gate

17 September 2026. Statuses are PASS / FAIL / BLOCKED / NOT TESTED. PASS is limited to the stated test environment. **Production status: NOT READY.** The local application is available for preview; there is no configured staging or production deployment.

| Gate | Status | Evidence / required action |
|---|---|---|
| Module inspection | PASS | Source review and classifications in production-readiness-audit.md |
| Security/permission regressions | PASS | 58-test suite; IDOR/scope/MFA/CSRF/snapshot/token/logging regressions |
| Formatter/linter/configured type checks | PASS | Ruff; mypy 60 application files, strict critical boundaries; Django checks |
| Repository-wide strict typing | FAIL | Dynamic framework/command/script boundaries remain unannotated; developer work |
| Complete dynamic UI localization | FAIL | Catalogs populated; remaining dynamic wording requires exhaustive developer pass |
| Concurrency/load | PASS | 3,000 requests without duplicates; delayed 16-worker single-ticket contention |
| Backup/database/private files | PASS | Encrypted disposable and retained restoration; 57 tables/file/credential verified |
| Auth/MFA mechanisms | PASS | Real password/TOTP enrollment/replay/session/CSRF checks |
| Critical real accounts | BLOCKED | Organizer bootstrap, individual MFA and recovery custody |
| Registration/ticket lifecycle | PASS | Verified lifecycle, approval, capacity, cancellation/revocation/expiry and token replay |
| Volunteer/department/task operations | PASS | Connected workflow and scope/dependency/shift tests |
| Speaker/program operations | PASS | Readiness/publication/schedule workflow tests |
| Local notifications | PASS | Local delivery, language selection, retries, deduplication, future scheduling |
| Real email | BLOCKED | SMTP/sender/DNS, approved templates and authorized inbox evidence |
| Private files | PASS | Authorization, quarantine, upload limits/signatures and hash-change tests |
| Malware engine | BLOCKED | Engine/signatures/mount permissions and clean/EICAR rehearsal |
| Reports/export | PASS | Connected attendance totals and read-only admission CSV; scoped/formula-protected exports |
| Accessibility/LTR/RTL automation | PASS | Selected axe rules and mobile layout checks; screenshots reviewed |
| Physical devices/screen readers | NOT TESTED | Actual Android/iPhone/tablet/browser and assistive-technology matrix |
| Final image/local startup | PASS | Rebuilt image; fresh migrations, non-root Gunicorn, health and headers |
| Real staging HTTPS/DB grants | BLOCKED | Host/domain/TLS and restricted runtime database role |
| Monitoring/alert receipt | BLOCKED | Local health/heartbeat tests pass; external probes and alert exercise absent |
| Off-host recovery/RPO/RTO | BLOCKED | Destination, key custody, retention approval and deployed timing |
| Manual fallback software | PASS | Entry-mode freezing, ledger preview/import/replay tests |
| Manual fallback with staff | NOT TESTED | Physical roster/outage/reconciliation exercise |
| Approved event configuration | BLOCKED | Room/doors/capacity/admission/privacy/languages/branding |
| Paid ticketing if selected | BLOCKED | Provider approval/integration/sandbox evidence; paid mode fails closed |

## Explicit release answers

- **Security:** reviewed software can be exercised in isolated staging with synthetic data; real staging configuration is BLOCKED. This is not an independent penetration-test certification.
- **Data:** local encrypted database/file/credential restoration PASS; off-host disaster recovery BLOCKED.
- **Authentication:** mechanisms PASS; protection of all real critical accounts BLOCKED because those accounts and custodians are not configured.
- **Permissions:** tested role/event/department/ownership boundaries PASS; deployed role assignments require review.
- **Registration / tickets / QR:** tested free-registration lifecycle and concurrency PASS. Paid admission is not implemented without provider selection.
- **Volunteers / departments / tasks / speakers / schedule:** connected workflows PASS in the synthetic application rehearsal.
- **Communications:** local outbox/template/retry tests PASS; real delivery BLOCKED.
- **Files:** private authorization/quarantine PASS; malware engine and deployed ACLs BLOCKED.
- **Reports:** tested database aggregates/exports PASS; physical attendance reconciliation NOT TESTED.
- **Event day:** software procedures documented and automated workflows PASS; actual staff/device operation NOT TESTED.
- **Failure:** manual-mode/import software PASS; real staff-led outage rehearsal NOT TESTED.

Do not enable real intake or entrance until mandatory gates pass. A passing build, a preview URL or a populated translation catalog is not an event-readiness declaration.
