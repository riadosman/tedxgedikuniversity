# 12 — Acceptance criteria and testing plan

> Implementation update, 17 September 2026: the organizer has authorized the full platform. Statements below about a documentation-only phase, an MVP, or tests not yet run describe the discovery baseline. See [current implementation and evidence](../development/implementation-status.md) for the implemented system and remaining gates.

Status: specifications only. **None of these application tests has run; no application exists.** Discovery documentation checks are recorded separately in the index/inventory.

## Test layers

Unit: status transitions, QR parser, normalization, authorization policy evaluation, consent decisions, CSV escaping and timing validation. Integration: real PostgreSQL constraints/locks, outbox, token lifecycle, approved provider sandbox contracts. E2E: browser journeys and staff role boundaries. Physical: actual phones, lighting, camera permissions, venue network, arrival handling and fallback. Recovery: real isolated restore and reconciliation. Do not replace concurrency tests with SQLite or mocked ORM assertions.

All identities, mailboxes, provider keys and payment events in CI/staging are synthetic/test values. Test delivery goes to controlled mailboxes; never broadcast to the event roster during validation.

## Acceptance scenarios

| ID / criticality | Scenario and expected result | Evidence / test type | Requirement coverage |
|---|---|---|---|
| AT-01 / P0 | A visitor reads published event details; editor changes draft room/name; public revision remains unchanged until organizer approves. No placeholder QR/speaker is advertised as functional/confirmed | Browser E2E and content review; check every required page and mandatory branding gate | FR-01,02,24; C01–C05 |
| AT-02 / P0 | Submit same event/email twice, verify twice, retry after timeout; one attendee/registration/ticket at most. Unverified request allocates no seat. Generic response does not reveal an existing registrant | Unit + database + E2E; inspect counts and delivery records | FR-03,04,05,06 |
| AT-03 / P0 | Start with limit 100 and 99 committed places; send 20 eligible simultaneous allocations on separate DB connections. Exactly one additional allocation, remaining requests waitlisted. Repeat at lower approved limit and across import/manual paths | Real PostgreSQL integration; count and audit invariants | FR-03,05,08; NFR-07,14 |
| AT-04 / P0 | Two simultaneous requests with distinct IDs and the same valid credential produce one NEW_ADMISSION and one ALREADY_ADMITTED. Repeat 100 times with fresh fixtures. Same-ID retry returns original receipt without new admission; changed payload with same ID rejected | Independent DB connections/processes and browser double-submit | FR-09,10,28; NFR-02,14 |
| AT-05 / P0 | Wrong event, malformed/truncated QR, random credential, revoked generation, cancelled/expired ticket and not-open event fail without admission. Reissued ticket cannot be admitted a second time if previously used | Unit/integration/E2E; raw QR absent from logs | FR-06,09; NFR-04 |
| AT-06 / P0 | Race cancellation, reissue and check-in using documented lock order. Either cancellation precedes entry and entry fails, or admission succeeds and slot stays consumed. Checkout never admits a replacement audience | Transaction integration; verify no deadlock leakage or extra slot | FR-05,07,09,34 |
| AT-07 / P0 | Every role attempts another event/department/owner ID via URL, API, form, file and export. Deny unauthorized rows/fields. Leader in A plus volunteer in B cannot manage B. Revoked member loses access within 60 s | Generated role/resource tests plus targeted E2E | FR-12,13,18,26,27,28; NFR-02 |
| AT-08 / P0 | Email provider unavailable, worker crash before/after provider acceptance, retry, stale cancelled ticket and hard bounce. Confirmed seat remains singular; failed mail is visible; stale credential is not resent as current | Outbox integration, controlled provider mailbox; inspect headers and safe logs | FR-04,06,07; NFR-13,14 |
| AT-09 / P0 | Session expires during scan; user denies camera permission; phone lost and account sessions revoked. No unauthorized admission; UI offers login/manual route and stops showing stale success | Physical iOS/Android + E2E | FR-09,10,12,13; NFR-01,08,09 |
| AT-10 / P0 | Disconnect network after server commit before response; preserve request ID. Declare manual mode, stop all devices, reconcile unknown entry, run single manual desk, restore and import ledger twice. No second admission or cap breach | Full team rehearsal, timed ledger comparison and signed supervisor record | FR-09,10,11,34; NFR-06,18 |
| AT-11 / P0 | CSV formula payload, duplicate rows, foreign event IDs, malformed encoding, oversized files, executable disguised as PDF and unauthorized private URL | Unit/integration/E2E; ensure quarantine and no partial unsafe import | FR-08,26,27; NFR-04,15 |
| AT-12 / P0 | Keyboard and screen-reader user completes registration and error recovery; staff use non-camera search; text/icon conveys every scanner state. Check layout/contrast/zoom in approved locales | Automated accessibility + manual assistive-tech audit | FR-01,04,09,10; NFR-10,11,12 |
| AT-13 / P0 if integrated | Applicant accepted without privileges; organizer separately assigns role. Leader assigns only own members, overlap fails, volunteer acknowledges own shift, replacement requires briefing, reassignment removes old access | Workflow integration/E2E; compare external roster if module deferred | FR-14,15,16,17,18 |
| AT-14 / P0 | Run documented scan load and 100 physical presentations; meet NFR-07/08 targets on recorded devices/network. Fast UI animation without committed admission does not count | Load metrics and actual-device timings | FR-09,10,25; NFR-07,08,12 |
| AT-15 / P0 | Decline/withdraw survey permission; registration still works; survey export excludes subject. Verified correction/deletion request follows approved hold/retention rules; unverified requester receives no data | Privacy E2E + purge dry-run and actual synthetic deletion | FR-26,29,33; NFR-03 |
| AT-16 / P0 | Restore database/files in isolated environment; recover keys, compare counts/checksums, reapply later revocations/deletions and reconcile admission ledger. Do not reopen while unknown admission status remains | Timed restore log meeting RPO/RTO; operator/deputy sign-off | FR-11,30; NFR-06,16 |
| AT-17 / P0 | Scan tracked files/build/output for secrets; production debug disabled; TLS/cookies/CSRF/headers checked; malicious payloads cannot expose QR/session/PII in logs, caches or referrers | Security checks and manual review; report locations without secret values | FR-06,12,27,28,30; NFR-01,04,13,16 |
| AT-18 / P0 only if paid | Invalid signature, replay, client redirect alone, amount/currency mismatch, duplicate callback, out-of-order failure/success, late success after hold expiry, provider timeout and repeated refund | Approved provider sandbox plus integration; never issue extra seat or mark unverified refund complete | FR-31,32; NFR-14 |
| AT-19 / P0 operational | Task with critical missing evidence cannot complete; dependency cycle fails; stale edit conflicts; publish runbook version and update critical cue; relevant staff acknowledge. Critical incident uses direct escalation then log | Integrated E2E or documented shared-tool rehearsal | FR-19,20,21,22,25 |
| AT-20 / P0 operational | Talk missing rights/release or unresolved claim cannot be marked ready; approved script edit invalidates approval; public bio publishes separately; duration/window errors rejected | Speaker-manager walkthrough and record inspection | FR-02,23,24,27 |
| AT-21 / P0 | Dashboard counts reconcile exactly to registrations/tickets/first admissions; refresh failure shows unavailable/stale, not zero. Export respects scope, timestamps and UTF-8 round-trip | Database assertion and browser tests | FR-25,26,28; NFR-15 |
| AT-22 / P0 operational | Closeout staff prepare consent-filtered survey and rights-approved media handoff, record official-tool completion references, retain required evidence and schedule deletion | Tabletop rehearsal before event; real completion verified after | FR-23,26,29,33 |

## Release gates

- **Public launch:** AT-01/07/12/17 applicable website/auth parts; privacy gate approved. Private source files inaccessible through all public routes.
- **Registration launch:** AT-02/03/05/06/08/11/15/16/21 and all shared P0 authorization/security checks pass. If paid, AT-18 also passes before payment links are enabled.
- **Door readiness:** AT-04/09/10/14/16 and critical operational scenarios pass on actual venue setup; named operator and deputy trained.
- **Optional modules:** their failures must not block the working admission system. Disable incomplete UI/routes and mark external alternative; do not ship fake dashboards.
- **Post-event completion:** AT-22 real evidence, financial reconciliation if applicable and retention handoff; a rehearsal alone does not prove actual submission.

## Test record template

For each scenario record test ID, commit/release, environment/DB version, device and browser if relevant, dataset, timestamp, operator, expected result, actual result, logs/screenshots without secrets, issue ID, retest result and reviewer. P0 failures require remediation or a tested scope alternative; accepting risk cannot turn a failed atomicity/privacy test into a pass.

Current test status: **not run — discovery only**. Documentation checks do not establish operational, legal or production readiness.
