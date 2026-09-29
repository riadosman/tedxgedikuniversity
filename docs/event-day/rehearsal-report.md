# Event rehearsal report

Environment: isolated PostgreSQL test database, synthetic identities, real Django HTTP endpoints and Chromium on Windows. No test people were loaded into the event database and no external messages were sent. Final results are in the readiness checklist.

| Sequence | Application evidence |
|---|---|
| Registration → verification → approval → ticket → QR | Browser forms, encrypted outbox link and database decisions |
| QR delivery/decoding → entrance → retry | Shipped decoder processes actual generated PNG; server commits actor/time; deliberately lost response safely retried |
| Volunteer application → acceptance → account/role → department/shift | Public/staff routes and transactional workflow test |
| Task assignment/dependencies/review | Ownership/scope, cycles, prerequisites and stale edits tested |
| Speaker → talk readiness/approval → schedule | Private/public content and publication prerequisites tested |
| Event-day login/MFA | Real browser password login plus TOTP enrollment/replay tests; production requires MFA |
| Manual lookup/admission, duplicate, ledger reconciliation | Scanner/services and controlled import/replay tests; physical identity policy needs staff rehearsal |
| Incident → resolution → announcement/read → program update | Database workflows and notifications |
| Reports/export | Database aggregates, scoped CSV, formula defense and consent handling |
| Backup/post-event | PostgreSQL/file restore separately; retention-hold/anonymization tests preserve history |

Repeated sustained run: 3,000 requests at 10 requests/second for five minutes; 100 first admissions and no duplicates. Local service p95 166.25 ms/p99 253.63 ms. A 16-worker same-ticket test includes a 300 ms database lock delay and requires one new admission plus fifteen already-admitted results. Constraints prevent attendee/ticket identity mismatch and duplicate admission.

Failure tests include network uncertainty, modified/wrong/revoked/expired/unverified credentials, access denial, changed retry payload, ledger replay, failed/scheduled/localized mail and missing heartbeats. Physical power/network failover, phones, real queue throughput, safety communication, actual SMTP/scanner and off-host keys are NOT TESTED here.

Execute the same chain on real staging HTTPS with named organizer, registration staff, leader, volunteer and program staff. Add actual devices, authorized inboxes, engine/provider checks and controlled paper-ledger outage. Record time, operator/device, step result, incident and reconciled physical count. Supervisor/technology lead sign-off remains required.

## Final local execution

The full suite passed 58 tests in 67.27 seconds. `test_team_program_and_operations_rehearsal` now executes a connected registration-to-attendance-export sequence through real Django routes, including actual QR PNG issuance, volunteer/department/shift/task assignment, approved speaker/program content, incident resolution and announcement acknowledgment. Browser/MFA/lost-response tests and the encrypted retained-restore test add independent evidence. Database fixtures are synthetic; SMTP inbox delivery and physical admission are not simulated as successful provider/device tests.

The connected rehearsal found the missing staff admission-history/export route. It is now a read-only, organizer/event-admin authorized resource, with audited purpose-required CSV export. One short service-latency test under simultaneous image building missed the 500 ms p95 gate; isolated and final runs passed. Final Docker rehearsal passed fresh migrations, non-root startup, database health and headers.
