# Implemented application architecture

Status: implementation in progress; see the [test and completion record](../development/implementation-status.md). The historical [discovery architecture](../technology-discovery/08-technical-architecture.md) explains the tradeoffs and source constraints.

## Runtime and module boundaries

Python 3.11, Django 5.2 LTS, PostgreSQL 15+, Django ORM/migrations, Django sessions and Argon2 passwords, django-otp TOTP/recovery codes, server-rendered templates, CSS and a small JavaScript QR scanner. Browser QR decoding uses locally vendored jsQR 1.4.0. Requirements and browser assets have lockfiles. Linux deployment uses Gunicorn and WhiteNoise behind a trusted HTTPS reverse proxy. No microservices, Redis or Celery are required.

| Module | Responsibility |
|---|---|
| `core` | Event policy, authentication views, permissions, CMS snapshots, staff resource forms, audit, privacy, operator commands |
| `admissions` | Minimal attendee registration, immutable notice acknowledgements, immediate tickets, credentials, action tokens, transactional check-in, receipts, entrance-ledger reconciliation |
| `team` | Applications, volunteer profiles, departments, memberships, shifts, briefing/attendance |
| `program` | Private speakers/talks, rights/release/fact checks, rehearsals, public schedule snapshots |
| `operations` | Tasks, dependencies, comments, incidents, runbook, operational contacts |
| `communications` | Targeted announcements, read receipts, editable email templates, encrypted outbox jobs |
| `documents` | Private file metadata, quarantine, constrained uploads and authorized downloads |
| `payments` | Conditional order/payment/refund data and provider interface; live integration remains unavailable |

`core/resources.py` defines explicit editable fields and list columns. Generic staff screens call `core/workflows.py`, not unrestricted Django admin. Public code reads only approved page/speaker/schedule snapshots. Event policy itself is organizer-only and version checked. Models validate data; services enforce business transitions and object authorization; PostgreSQL adds relational constraints and immutable historical records.

## Transactions and authority

Allocation, cancellation, QR rotation, manual-mode changes, CSV commit and event settings take an exclusive event row lock first. Check-in takes a PostgreSQL shared event lock and an exclusive ticket lock: different entrance desks may process different tickets concurrently, while event/ticket changes and duplicate scans remain serialized. A request-scoped transaction advisory lock serializes concurrent retries before reading their durable receipt. One ticket belongs to one registration and one attendee. Composite foreign keys enforce matching event IDs and ticket/registration/attendee identity, including direct SQL mutations. Check-in has a unique ticket key. PostgreSQL triggers reject updates/deletes to audit and first-admission rows.

The scan endpoint accepts a UUID request ID. A durable receipt is scoped to event + actor + request ID and bound to an input fingerprint. The same request returns its original result; changing the input with the same ID fails. A distinct scan of an admitted ticket returns `ALREADY_CHECKED_IN`. Cancellation after admission never frees its lifetime audience place.

Public registration creates the attendee, immutable privacy-notice acknowledgement, ticket and encrypted QR credential in one transaction under the event lock. Email is optional and queued after commit. New QR payloads use an opaque `tx2.` token with 32 random bytes; public ticket references are separate from database keys. Legacy records and credentials are preserved. See [ticketing operations and migration](../operations/immediate-ticketing.md).

## Source-backed event import

`import_event_sources` parses F01–F04 and F10 from the reviewed facts table, retaining source references. It creates unpublished event settings and draft pages and leaves intake closed. Existing content is preserved. The repository's original correspondence, PDFs and artwork are never copied to public static files. Speaker names, final theme, exact room, approved languages and ticket price are not invented.

## Data and deployment boundaries

Database credentials, Django signing secret, QR encryption key and independent backup encryption key come from environment configuration. New QR payloads contain only a format marker and 256 random bits; legacy QR payloads additionally contain the event UUID. Neither contains attendee data. Lookup uses SHA-256; re-delivery material and outbox link payloads use Fernet encryption. No payment-card data is stored. Private files live outside static assets and cannot be downloaded without a fresh permission check.

Deployment uses only `platform/` as its build context. Database migrations run as a release operation. Web workers do not run email delivery. A scheduled `deliver_notifications` command leases jobs in short transactions and performs I/O after releasing locks. SMTP acceptance is recorded as sent, not proof of inbox delivery; a crash after acceptance can produce duplicate mail, but never another ticket.
