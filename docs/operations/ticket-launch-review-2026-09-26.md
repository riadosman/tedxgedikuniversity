# Ticket launch review — 26 September 2026

> Historical review of the replaced implementation. The verification/review flow described below has been retired. Use [Immediate ticketing](immediate-ticketing.md) for current behavior and setup.

**Conclusion:** the tested local free-ticket lifecycle works. The current event configuration is not ready for public registration. No production URL exists for this review.

## Initial event findings (before follow-up)

Read-only inspection of the configured `tedx` database found:

| Priority | Finding | Consequence / action |
|---|---|---|
| Launch blocker | General admission (`general`) is the only category and is disabled. | Staff approval cannot allocate a ticket. Enable the approved category in Ticket types before intake. |
| Launch preparation | Event is published, review registration is enabled, and the current date is within its registration window. | The local form already accepts applications. Confirm whether this is intentional before exposing the server. |
| Launch preparation | Privacy approval is false; the notice version is `2026-09-17-draft-2`. | The registration form omits the acknowledgement. Current code intentionally permits this and records `not-published`; obtain the actual approval before launch. This review did not change that product policy. |
| Link configuration | PUBLIC_BASE_URL is `http://127.0.0.1:8000`, but that port serves another local application. | The TEDx preview started for this review uses `http://127.0.0.1:8765`. Align the origin before using email links and use the real HTTPS origin when deployed. Automated tests override the origin to their isolated server. |
| Email verification pending | SMTP backend is selected; two existing notification jobs are pending. | SMTP configuration alone is not proof of delivery. No real inbox test or production worker verification was performed. Do not infer that the pending jobs are failed or stale from their count alone. |
| Event-day preparation | Entrance mode is closed; admission opening time is unset. | Set the actual doors time and rehearse before switching to Online. Closed entry is appropriate before event day. |
| Inventory | 0 tickets; 1 submitted registration; capacity 100 / licence ceiling 100. | There were no real existing tickets to audit. Existing-ticket verification was tested using synthetic tickets. |

The public homepage, registration, recovery and team login pages returned HTTP 200 on port 8765. The registration page clearly explains the review workflow, shows event date/time/venue, and provides a recovery link. Visual inspection found a legible desktop form and mobile synthetic ticket. Selected accessibility checks passed in the existing browser rehearsal; this is not an exhaustive accessibility review.

## Executed checks

56 existing tests passed across:

- `test_admission.py`: lifecycle, capacity/waitlist, invalid/wrong-event requests, duplicate and concurrent scans, durable request identity and event boundaries.
- `test_registration_policy.py`: the current approved/unapproved notice behavior.
- `test_security_recovery.py`: competing allocations, MFA replay, permission scopes, immutable history, manual ledger replay and privacy recovery.
- `test_hardening.py`: event/role boundaries, private uploads and selected ticket categories.
- `test_browser.py`: real Chromium registration, verification, staff approval, QR decoding, interrupted scan-response recovery, selected accessibility checks and mobile layout.
- `test_workflows.py`: staff pages, duplicate registration, token behavior, local mail deduplication, MFA and CSRF, plus operational workflows.
- `test_email_monitoring.py`: localized email, retry behavior, missing templates and monitoring signals.
- `test_readiness_security.py`: malformed scan requests, expiry/tampering/unverified checks and additional authorization/data invariants.

Two new parametrized checks in `platform/tests/test_ticket_launch_review.py` passed for **review** and **first_come** modes. Each creates synthetic data through the registration endpoint, verifies email, allocates a ticket, opens the issued email's ticket URL in Chromium and decodes the actual PNG served to the attendee using the shipped jsQR decoder. Each confirms:

1. Submission and verification-link GET do not silently allocate/verify.
2. Review requires approval; first-come allocates after verification.
3. Exactly one confirmed ticket and current credential exist.
4. Reference lookup finds the ticket without creating an admission.
5. The mobile ticket shows the attendee and booking reference without horizontal overflow.
6. The displayed QR produces NEW_ADMISSION once and ALREADY_ADMITTED subsequently.
7. Rotation revokes the old QR and preserves admission history; the replacement does not grant another entry.
8. Cancellation prevents further access to the ticket QR image, while preserving the single admission record.

Django system check: no issues. Ruff lint passed; the new test was formatted with Ruff. A Django transitional-setting deprecation warning remains; it did not fail the tests.

## Evidence and run history

- `.local/test-artifacts/ticket-review-results.xml`: 56 existing passes plus 2 initial failures in the newly added test harness.
- Those two failures were caused by injecting an inline decoder script, correctly blocked by Content Security Policy. The test now loads the site's own static decoder URL; no application security policy was weakened.
- `.local/test-artifacts/ticket-qr-results.xml`: corrected focused run, **2 passed**, 35.22 seconds.
- `.local/test-artifacts/ticket-review-run.log` and `ticket-qr-run.log`: execution details.
- `.local/test-artifacts/ticket-launch-review.png` and `ticket-launch-first_come.png`: synthetic ticket screenshots.
- `.local/test-artifacts/local-home.png`, `local-registration.png`, `local-recovery.png`, `local-login.png`: current preview pages.

An initial run was interrupted after starting with the local database stopped. Reusing the interrupted test database caused fixture collisions; rebuilding the isolated test database resolved them. The clean rebuilt run produced the 56 passes above. No event database was reset.

Reproduce the focused test from `platform/`:

```powershell
../.venv/Scripts/python.exe -m pytest tests/test_ticket_launch_review.py -q
```

Do not run competing pytest processes against the same test database. The tests use PostgreSQL's isolated test database and `.invalid` identities. No real email was sent during this review.

## Remaining verification

- Real SMTP delivery for verification, issuance and recovery; correct public origin; approved templates in every enabled language.
- HTTPS deployment, worker scheduling, account/role assignment, monitoring and deployed backup restoration.
- Physical camera capture and venue connectivity; staff-led outage rehearsal.
- Invitation-mode end-to-end rehearsal if selected; paid admission is not implemented by the current free-ticket workflow.
- No existing real tickets could be validated because the event has none.

Private email access/verification links currently expire after 30 minutes from creation. A delayed email worker can therefore deliver an already-expired link. Keep the worker running and rehearse recovery; attendees should print/save the ticket promptly. Ticket expiry itself is set to the event end when allocated.

## Deliverables and changes

- `output/ticket-review/operating-guide.pdf`: eight-page simple guide.
- `output/ticket-review/operating-guide.html`: editable/printable source, with a synthetic screenshot beside it.
- This findings report.
- `platform/tests/test_ticket_launch_review.py`: two additional reusable lifecycle checks.

Started the existing local PostgreSQL cluster and the TEDx development preview on port 8765. Production/event settings, the existing registration and real admission records were not changed. No ticketing application code was modified. The disabled category and approvals were documented rather than silently changed during a review.


## Follow-up after the request to continue

- Enabled the existing capacity-counted General admission category in the local event. The model was validated, its version incremented, and an audit record recorded the local configuration change without impersonating a staff account.
- Set the private local environment's PUBLIC_BASE_URL to `http://127.0.0.1:8765`. Updated the matching local CSRF origin if explicitly configured. No secrets were printed.
- Restarted only the identified TEDx preview processes to load the new configuration.
- The two pending email payloads were inspected without exposing recipient data or tokens; both contain port 8000. They were not rewritten or sent. Request fresh links after confirming email delivery; do not treat these old queued messages as valid test evidence.
- Privacy approval, entrance opening time, entry mode, publication, real registrations and real tickets were left unchanged.
- The PDF/HTML operating guide has been updated to reflect these corrections.

Remaining launch work: actual privacy approval; authorized inbox delivery checks; production HTTPS/worker/backup setup; actual doors time and physical device rehearsal. Localhost links are only usable on this computer.

### Follow-up validation

All **58 tests passed in one fresh run** (51.17 seconds), with one non-failing Django deprecation warning. Evidence: `.local/test-artifacts/ticket-followup-results.xml` and `ticket-followup-run.log`. The restricted browser subprocess attempt was replaced by the approved outside-sandbox run.

Read-only post-change verification confirmed General admission enabled, PUBLIC_BASE_URL on port 8765, 0 real tickets, 1 real registration, privacy approval still false and entry mode still closed. The restarted public registration page returned HTTP 200. The updated PDF contains eight laid-out pages with no detected content overflow or footer overlap.
