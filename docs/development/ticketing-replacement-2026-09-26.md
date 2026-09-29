# Integrated ticketing replacement — 26 September 2026

The existing Django admissions module now issues a ticket immediately after valid registration. There is no second application, attendee account system, external verification dependency or new SaaS service. Event/program/team/CMS/authentication infrastructure remains in place.

## Delivered behavior

- Public registration collects name, email and the required acknowledgement of the applicable information notice. Extra attendee questions, survey-consent gating, approval/waitlist issuance and mandatory email verification are retired. Newsletter functionality is not implemented, so no marketing checkbox or marketing consent gate is added.
- Email is validated and compared case-insensitively using the existing event identity convention; dots and plus tags are retained. Duplicate registrations return a clear message without an existing ticket link or identity details.
- An exclusive event transaction creates the attendee, immutable notice acknowledgement, ticket and encrypted QR credential together. Capacity and duplicate-email checks are authoritative in PostgreSQL.
- Public ticket references contain 96 random bits and are separate from database UUIDs. New QR credentials contain 256 cryptographically random bits with a format marker, never personal information or database IDs. Legacy credentials remain supported.
- The private confirmation page displays the ticket and printable QR immediately. Email queuing happens after commit and delivery status remains separate. Provider/queue failures cannot invalidate a ticket.
- Authorized entrance staff scan through the existing interface. PostgreSQL shared event locks permit different tickets to be checked concurrently; exclusive ticket locks prevent double admission. A transaction advisory lock serializes duplicate request IDs before durable receipt lookup. Cancellation and event-setting changes still obtain exclusive event locks.
- Existing admin lists support name/email/ticket-reference search, status/timestamps, audited corrections, cancellation, credential rotation and minimum-field CSV exports without QR secrets. The TEDx survey export contains checked-in attendee emails for manual uploading.
- Retention duration and purpose are configurable. The existing verified privacy-request/anonymization process checks the configured policy and holds. No automatic deletion or invented statutory period is introduced.

## Main changed modules

| Area | Files/modules |
|---|---|
| Models and transactions | `admissions/models.py`, `admissions/services.py`, `core/models.py` |
| Public UI and private ticket | `core/forms.py`, `core/public_views.py`, public registration/ticket templates, language catalogs |
| Staff operations | `core/views.py`, `core/resources.py`, `core/workflows.py`, `core/permissions.py`, scanner JavaScript and staff templates |
| Privacy and transport | `core/privacy.py`, `core/middleware.py`, `core/logging.py` |
| Optional communications | Existing `communications` outbox, templates/worker and `config/settings.py` |
| Source copy | Registration/FAQ draft copy in `content/event-pages.json` |
| Verification | `tests/test_immediate_ticketing.py`, updated existing admission/browser/security tests |

## Migration and local state

An encrypted backup was created at `.local/ticketing-before-replacement.enc` using the existing backup tool before applying migrations. Encryption keys stay in the private environment configuration and are not included in this report.

Applied locally: `core/0010`, `admissions/0004`, `communications/0003`, `core/0011`. They add the notice/acknowledgement records, ticket timestamps and optional email/retention settings; map historical ticket states; retire unsent verification emails; and update unchanged imported CMS drafts. They do not erase attendee history or fabricate notice acknowledgements. Published CMS snapshots remain subject to organizer review/publication.

The local database retained its one attendee and one historical registration, with zero issued tickets and zero fabricated acknowledgements. The old review mode was migrated to immediate registration. The actual privacy approval is still false; intake correctly remains blocked. The application did not approve legal wording or send test emails to real attendees.

## Verification results

- Final regression: **102 passed**, covering all current tests except the two extensive visual matrices (`test_design_browser.py` and `test_product_review.py`). Those two matrices passed in the preceding full run; the subsequent changes were confined to check-in locking/persistence and its concurrency tests, plus documentation.
- The preceding full run had **101 passed / 1 failed**; the failure was the entrance latency target, subsequently fixed and retested. No threshold was relaxed. The final run added concurrent identical/conflicting request-ID tests.
- Final local load rehearsal: 20 requests at 10 requests/second using five workers, 20 unique admissions; p95/p99 service latency **293.96 ms**, against the existing 500 ms / 1,500 ms limits. This measures the isolated local PostgreSQL service boundary, not production network or camera performance.
- Ruff passed. Mypy passed for 65 source files. Django system checks passed. `makemigrations --check --dry-run` reported no missing model migrations.
- The browser rehearsal submits the minimal public form, receives the ticket immediately and exercises the existing staff workflow. The ticket-image lifecycle test decodes the QR served by the application. Tests use synthetic identities and an isolated PostgreSQL test database.
- The six-page PDF was rendered and checked for page/footer overflow; cover and closing pages were visually inspected. The local registration page returns HTTP 200 and displays the privacy-approval gate.
- Evidence: `.local/test-artifacts/ticket-release.xml`, `ticket-release.log`, `load-2s.json`; preceding complete visual run: `ticket-final.xml`. The one remaining warning is Django's existing transitional URL-field setting deprecation.

## Operating documents

- [Six-page Turkish PDF](../../output/ticket-review/operating-guide.pdf)
- [Printable HTML source](../../output/ticket-review/operating-guide.html)
- [Detailed operating and upgrade notes](../operations/immediate-ticketing.md)

Local preview: `http://127.0.0.1:8765/`. This is a development preview, not a production deployment. Before launch, the organizer must approve the real privacy notice, verify event settings, publish reviewed registration/FAQ copy and rehearse camera/HTTPS/connectivity on the actual venue devices.
