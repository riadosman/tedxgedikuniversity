# TEDx Gedik — immediate ticketing

This replaces the earlier email-verification/review instructions. Ticketing remains inside the existing Django application; staff accounts, event settings, PostgreSQL, QR scanner and email outbox are reused.

For a simple Turkish overview, use the [six-page PDF guide](../../output/ticket-review/operating-guide.pdf). Implementation and verified results are recorded in the [replacement report](../development/ticketing-replacement-2026-09-26.md).

## Open registration

1. In Event settings, confirm free admission, capacity, venue, dates and the registration window. Capacity remains bounded by the existing licence ceiling.
2. Enter the approved **KVKK Aydınlatma Metni**, assign its version and confirm actual notice approval. The application does not approve legal wording. Changing previously acknowledged text requires a new version.
3. Enable the existing `general` ticket category. Choose **Open — immediate tickets** and publish the event. The allocation cutoff, if set, must also allow registration.
4. Check the public form. It collects full name, email, mobile phone, whether the attendee will come by car (and the vehicle plate if so, for parking reservation) and a required notice acknowledgement. There are no custom demographic fields, survey opt-in gate or newsletter checkbox. No newsletter functionality has been added.
5. Complete a rehearsal with synthetic data on staging. Registration immediately shows a private ticket page with the attendee name, public ticket ID, event details and QR. Print/save it. No attendee account or verification email is required.

### Phone, car and parking

The mobile phone (10–15 digits, `+` allowed) and the "Will you come by car?" answer are required. The plate field appears only after **Yes** and is then required. Plates are stored uppercase and grouped as printed (`34abc123` → `34 ABC 123`). A **No** answer stores no plate. Parking is not capacity-limited; staff build the parking list from the export by filtering `arrives_by_car = yes`. The plate is printed on the attendee's ticket and is searchable in the Attendees list. Attendees registered before this change have empty phone/plate fields and are not asked again.

Before deploying, add the new data to the KVKK Aydınlatma Metni under a new notice version: the phone number is processed to contact the attendee about the event day, and the vehicle plate (only from attendees arriving by car) to reserve and control parking access, with the venue/security staff as recipients if the plate list is shared with them.

### Attendance rules

The registration page and the ticket show an **Attendance rules** box. Its first line, "Doors open at HH:MM", comes from the event's admission opening time in Event settings. The rest is the CMS page with the key `rules` (TR/EN/AR drafts are created by `prepare_public_content`). Edit and publish it like any other page; an unpublished rules page is not shown. The rules are informational: registration does not require ticking a rules checkbox.

Duplicate email addresses get a clear message without displaying the existing person's ticket or details. A full event rejects the submission; it does not silently add a waitlist entry. Names and email addresses must be valid server-side. Email comparison is case-insensitive for compatibility with this event's existing records; dots and plus tags are preserved.

## Optional email

Ticket email is **off by default** per event. Enable `Ticket email enabled` only after templates and the existing SMTP/backend are ready. `PUBLIC_BASE_URL` must be the real HTTPS origin in production.

To operate without any outgoing email provider, set `OUTGOING_EMAIL_ENABLED=false`. Production still enforces HTTPS, secure cookies and staff MFA; only email-provider startup requirements are disabled. This setting pauses all outgoing communications, including staff invitations, so use the existing organizer bootstrap for initial access. It does not change authentication or disable MFA.

When email is enabled, schedule `deliver_notifications --limit 50`. Ticket creation commits first; confirmation is queued afterward. Queue or delivery failure cannot invalidate the ticket. Email delivery status appears separately in the existing Email delivery module; queue failures log only the error class. Confirmations include event, name, public ticket ID, date, venue and private access link. Check custom/localized templates before enabling them.

Private ticket links work until one day after event end, or at least 30 minutes from creation for post-event recovery. QR admission itself expires at event end. Lost links can be recovered by email if enabled; otherwise the organizer must verify identity and assist through the existing administrative records. A duplicate submission never discloses an old link.

## Tickets and entrance

Tickets expire at the event end time and manage links one day later. Changing the event end in Event settings moves the expiry of already issued tickets and unused manage links with it, so tickets issued before a date change stay valid at the door. The settings audit entry records how many tickets were moved.

- **Tickets:** search by name, email or public ticket ID. The list shows status, registration time, check-in time and cancellation time. Existing attendees can be corrected with a required reason after identity review; changing email revokes old management links and suppresses pending messages to the previous address.
- **Dashboard:** shows registrations, valid tickets, checked-in count, cancelled tickets, available registration capacity and remaining arrivals.
- **Entrance check-in:** requires an individual staff account and existing event permission. A successful scan records `CHECKED_IN` atomically and displays name, reference and time. A repeat shows `ALREADY_CHECKED_IN` with the prior time. Invalid/cancelled credentials are rejected without attendee details.
- **Scanning records admission.** Search is read-only; scanning is not a preview validator. A lost response must be retried with the same request ID. Existing controlled manual-ledger reconciliation remains available.
- Cancel and rotate tickets through their existing actions. Rotation preserves the public ID and admission history. A cancelled ticket that already admitted someone still counts against physical event capacity.

Set actual entrance opening time and switch entry mode to Online only when doors are ready. Rehearse camera permission, HTTPS and venue connectivity on real devices. The software requires an online backend decision.

## Exports and privacy

Authorized administrators use the existing Tickets/Attendees export with a purpose. CSV fields are name, email, phone, arrives by car (yes/no, empty for earlier registrations), vehicle plate, public ticket ID, ticket status, registration timestamp and check-in timestamp. No QR credentials, access tokens or database IDs are exported. Spreadsheet formula prefixes are escaped. Exports are audited and require recent MFA when MFA is enabled.

The **TEDx attendee email export** contains only emails for people with recorded admission. The general attendee export also contains registered/no-show/cancelled ticket records if needed for legitimate reconciliation. Neither export depends on marketing consent, and neither sends anything to TED. The organizer manually uses the official uploader after confirming the applicable notice, basis and transfer requirements.

Notice acknowledgements record attendee ID, type, immutable policy-version reference and timestamp. Notice text is stored once per event/version. Historical acknowledgements are never rewritten when an attendee corrects their name or the organizer publishes a new version.

Set **Retention days** and **Retention reason** after reviewing the post-event survey, applicable obligations and disputes. New events have no invented statutory duration. Existing configured durations are preserved, but a documented reason is required before erasure. A missing setting prevents automatic erasure; it is an unresolved operational decision, not permission to keep data forever. Schedule a named post-event review. No automatic attendee deletion is added.

Use the existing verified Privacy request → Anonymize workflow, with a reason and recent MFA. Active holds and the configured period block erasure. Identity, credential ciphertext, management links, answers and matching mail payloads are cleared/anonymized; permanent admission/audit integrity and pseudonymous acknowledgement references remain. Review external exports and backup expiry separately.

## Upgrade and existing records

Run committed migrations with `python manage.py migrate --noinput` after the normal backup procedure. No tables or attendee records are deleted.

- `core/0010`: adds optional ticket email and documented retention settings; converts old review/invitation intake modes to immediate registration. Closed events stay closed. Notice approval is not fabricated; intake remains blocked without it.
- `admissions/0004`: adds ticket timestamps, immutable notice versions and acknowledgements. Confirmed tickets become Registered, or Checked in if admission history exists; the timestamp is copied from that history. Cancelled/expired/pending historical records are preserved. Unknown historical cancellation/acknowledgement times are not invented.
- New credentials use `tx2.` plus 32 cryptographically random bytes encoded as URL-safe text. The QR contains no event/database ID or personal data. Existing `tx1` credentials continue to validate; they are not silently rotated.
- Old applications without a ticket remain historical records. They are not automatically approved or assigned fabricated acknowledgements. Their reserved email identity needs organizer review before re-enrollment; do not delete production data or issue tickets through ad-hoc SQL. Old verification links no longer issue tickets and show a retirement message.
- Old `verified_at`, `survey_consent`, registration answers and invitation records remain for historical evidence only. They do not gate new tickets. Normal registration/import interfaces no longer collect those fields; registration CSV import and invitation creation are retired. The controlled entrance-ledger import remains.
- `communications/0003`: adds safe ticket-detail placeholders to the existing templates and suppresses unsent obsolete verification messages. Custom wording is retained. Review it before sending.
- `core/0011`: updates unchanged imported FAQ/registration drafts to explain immediate tickets. Organizer edits and published snapshots are preserved; review and publish the updated drafts through the existing CMS.

The history constraints are forward-only. Roll back code only with a compatible schema; use the existing controlled backup/restore procedure for data recovery. Do not reverse/delete admission or acknowledgement history.

## Evidence and source boundaries

New acceptance tests: `platform/tests/test_immediate_ticketing.py`. Updated browser rehearsal: `test_browser.py`; actual ticket-image lifecycle: `test_ticket_launch_review.py`. Run from `platform/` with `../.venv/Scripts/python.exe -m pytest -q`. Tests use isolated PostgreSQL and synthetic identities; no real messages are sent.

Official sources checked on 26 September 2026:

- [TEDx attendee engagement guide](https://www.ted.com/tedx/organizer-guide/invite-and-engage-attendees) and [TED survey delivery guidance](https://help.ted.com/hc/en-us/articles/40919052885655-How-will-my-attendees-receive-the-TEDx-Attendee-Survey): explain the organizer's post-event uploader process and applicable local privacy considerations. The application supplies an export, not a TED integration or a legal basis.
- [KVKK information-notice guidance](https://www.kvkk.gov.tr/Icerik/6765/AYDINLATMA-YUKUMLULUGUNUN-YERINE-GETIRILMESI-HAKKINDA-KAMUOYU-DUYURUSU): distinguishes the information obligation from explicit consent. The required product acknowledgement is not blanket explicit consent.

These references do not establish an event-specific retention period or approve the university's notice. The responsible organizer/controller must make those decisions.
