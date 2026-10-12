# Implementation and verification record

Updated 17 September 2026. This records implemented behavior, not a production-readiness declaration. The organizer's full-platform request supersedes the historical discovery's MVP sequencing; no major operational module has been deliberately deferred to an MVP.

## Implemented

| Area | Working implementation | Principal evidence |
|---|---|---|
| Foundation | Django/PostgreSQL modular monolith, committed migrations, environment configuration, immutable audit/admission history, event foreign-key constraints | Django checks, fresh PostgreSQL migration runs, database tests |
| Authentication | Real password login/logout/change/recovery, account invitations, activation/deactivation, TOTP, recovery codes, idle/absolute session expiry, recent-MFA checks | Authentication/MFA/replay/CSRF tests; browser login |
| Authorization | Event roles, department/ownership scope, explicit form fields, scoped relations, export controls and private-download checks | Role/scope and mixed-role regression tests |
| Public website/CMS | Responsive event pages, draft/public snapshots, speaker/program pages, venue/policy/contact pages, editable translations by page language, safe unpublished states | Public snapshot/XSS tests; browser and accessibility checks |
| Registration | Closed/review/first-come/invitation settings, custom questions, email verification, generic duplicate/recovery responses, review/waitlist/cancel workflows | Registration tests and browser rehearsal |
| Tickets/check-in | Capacity allocation, encrypted high-entropy QR, revocation/rotation, staff/manual scan, permanent admission, durable retry receipts, mobile UI and live counts | Concurrent allocation/scanning, cancellation/rotation, browser lost-response recovery |
| Team | Applications, acceptance without automatic privileges, applicant withdrawal, profiles, departments/readiness, memberships, shifts, briefing/arrival/acknowledgment | Team workflow and overlap/scope tests |
| Program | Public/private speaker separation, release/fact/rights readiness, final approval, rehearsals, schedule validation/publication and private production cues | Program workflow tests |
| Operations | Tasks/dependencies/deadlines/comments, incidents/resolution, targeted announcements/read state, runbook publication/acknowledgment, operational contacts/dashboard | Workflow, cycle, stale-edit and runbook-snapshot tests |
| Files | Private uploads, size/type validation, quarantine, configured malware-scanner boundary, authorized download and approved public-photo route | Quarantine/private-access tests |
| Reports/privacy | Database counts, scoped CSV, formula neutralization, consent-filtered survey export, attendee self-export/correction, verified erasure review and anonymization with retention holds | Export/privacy tests; no public attendee list |
| Notifications | Editable templates, encrypted DB outbox, lease/retry/backoff, failed-job visibility/retry, registration/ticket/volunteer/account/schedule/announcement messages | Idempotency and local mail-backend tests |
| Recovery/deployment | Controlled roster/ledger import, repeated-import protection, encrypted backups, isolated restore verifier, non-root production image and production settings checks | Real PostgreSQL restore and disposable-container rehearsal |

## Executed checks — readiness audit, 17 September 2026

- **58 tests passed in 67.27 seconds** on real isolated PostgreSQL and Chromium. One Django 6 transition deprecation warning remains; no failed tests. The original 38-test baseline was also rerun before hardening.
- Formatter/linter passed. Mypy passed across 60 application files with additional strict checks on admission, authorization and other critical boundaries. This is not repository-wide strict typing; see [quality scope](code-quality.md).
- Connected rehearsal now covers registration/verification/approval/QR image, volunteer/department/shift/task assignment, speaker/talk/program, incidents/announcements, scanner admission/duplicate/manual lookup, accurate totals and admission-history CSV. MFA, lost HTTP response recovery and ledger reconciliation have additional dedicated tests.
- Twenty concurrent approvals at one remaining seat produced one ticket. Sixteen concurrent scanner workers with injected database lock delay produced one new admission and fifteen already-admitted results.
- A repeated five-minute service run processed 3,000 requests at 10 requests/second using five workers: 100 first admissions, zero duplicates, p95 166.25 ms/p99 253.63 ms. This excludes HTTP/network/device latency. One short test while Docker was building missed p95 at 507.64 ms; the isolated rerun and final suite passed. Preserve this sensitivity in staging capacity tests.
- Disposable and retained encrypted recovery both passed using a real test admission, encrypted ticket credential and private file. Database counts across 57 tables, file hashes and credential decryption were verified. Production data was not overwritten.
- Expanded axe/overflow checks passed on public/staff forms, tables, dashboard, reports and scanner; Turkish/Arabic mobile dashboard screenshots were reviewed. This does not certify WCAG compliance or physical-device compatibility.
- Updated image built and passed non-root UID 10001 Gunicorn startup, fresh migrations, PostgreSQL health, public/login pages and security headers. Production configuration rejects local email backends. Only domain-wide HSTS/preload advisories W005/W021 are intentionally excluded pending domain-owner approval; host HTTPS/HSTS remains enforced.
- Python production-lock and npm production-dependency audits reported no known vulnerabilities at this inspection.
- All 41 original event files match their recorded SHA-256 hashes. No synthetic attendees/accounts were added to the real event database.

## Remaining implementation/verification work

Critical boundaries are typed, but full repository-wide strict typing remains incomplete. Extracted English/Turkish/Arabic catalogs are populated and tested, but dynamic runtime wording needs a final exhaustive localization pass. These are developer tasks, not external business blockers. Native-language content approval, assistive technology and actual camera/network rehearsal remain separate gates. See the [readiness audit](production-readiness-audit.md) and [PASS/FAIL/BLOCKED/NOT TESTED checklist](production-readiness-checklist.md).

## External decisions and operating gates

- Confirm public identity/branding, audience allocation and counting policy, registration dates/mode, approved languages and privacy/controller text.
- Select free admission or an approved paid model. **No payment provider, hosted checkout, production webhook handler or refund integration is implemented.** The relational boundary and typed provider interface exist; paid intake fails closed. A provider-specific implementation/sandbox contract is required if paid tickets are chosen.
- Supply real hosting/domain/HTTPS proxy configuration, SMTP sender/DNS/provider account, malware scanner, persistent storage, off-host backup custody, monitoring and alert recipients. No external email or live deployment was performed.
- Name the entrance supervisor/deputy and rehearse actual iOS/Android camera phones, lighting, Wi-Fi/cellular fallback, physical roster control, power failure and restored-state reconciliation.
- Approve retention/holds and external-copy handling, and review source correspondence/official TEDx/university constraints before publication or data collection.

## Next work

Complete the remaining strict-typing/dynamic-localization work, then configure private staging with approved event settings, individual MFA accounts, SMTP, malware scanning, monitoring and off-host recovery. Rehearse actual devices and the manual entrance procedure. Keep real intake closed until the readiness gates pass.

Local preview runs at `http://127.0.0.1:8010/`; sign-in is `/accounts/login/`. Public content remains unpublished. Email-link origin still uses the existing port-8000 environment setting because automatic approval review blocked process reconfiguration; do not test email-link delivery using this preview. Preview is a development server, not a production deployment.

## Public website follow-up

The local preview now shows source-backed English/Turkish event pages, the supplied logo, expanded homepage and closed-registration information without unpublished-event 404s. See [website update](public-website-update.md). The follow-up suite passed 61 tests; 30 bilingual live-page checks passed. Use `http://127.0.0.1:8010/?lang=tr` for Turkish. Production publication and admission gates remain unchanged.


## Visual redesign follow-up

Shared public/staff design tokens, editorial homepage, supplied black/white branding, responsive navigation, accessible shared forms, digital ticket, mobile record layouts, department panels and scanner feedback are implemented. See [visual redesign and verification](visual-redesign.md). Final suite: 62 passed; Ruff, configured mypy and EN/TR/AR translation checks pass. Eight viewport widths (320–1920px), populated public/staff workflows and all resource routes were checked. Physical device and final content approval requirements remain open; production readiness status is unchanged.
