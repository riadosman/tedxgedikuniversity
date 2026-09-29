# 06 — Registration, ticketing and QR specification

Status: proposed ADR-02/03. Implements FR-03–11, FR-31/32/34. No ticket policy, provider or production system exists in the inspected workspace. **Free admission is not a confirmed event fact.**

## Model comparison

| Model | Advantages for this event | Risks / conditions | Recommendation |
|---|---|---|---|
| A. Free registration | No merchant onboarding, settlement or refund logic; small one-event scope | Still requires allocation, privacy, email and dependable entry operations | Preferred custom baseline if organizer confirms free entry and engineering capacity |
| B. External ticketing | Can reduce custom delivery risk; provider may own registration and scanner | Must verify local availability, fees, cap enforcement, scanner/offline behavior, exports and data handling | Preferred fallback; preferred paid route if approved vendor satisfies requirements |
| C. Custom registration + hosted payment | Custom experience with no card processing | Webhooks, reservations, reconciliation, late payments and refunds materially increase scope | Only with explicit paid gate and sufficient implementation/test time |
| D. Full custom ticketing | Broad control of inventory, pricing and orders | High scope and risk for 100 attendees and 34 days; card processing still external | Not justified for first event |

No vendor chosen. Price, currency, merchant entity, student/invite policy and fee/refund terms are Q01/Q12. If B is selected, it is the authoritative ticket source and scanner until a formally tested migration; do not run independently allocating custom and provider systems. Imported reporting copies are read-only. Mixed admission engines are prohibited unless a documented synchronization contract meets the same concurrency guarantees.

## Identity, policy and state machines

Proposed baseline: one general-admission type, one ticket per verified event/email, one attendee per submission, no group orders, transfers, resale, assigned seating or walk-in sales. Email verification proves mailbox control, not government identity or university enrollment. Duplicate-name and shared-mailbox cases go to the supervisor under approved policy; do not invent a requirement to upload ID. Preserve original address and use conservative trimming/case normalization; do not strip plus tags or dots as identity logic.

Default proposed allocation is verified first-come-first-served with a waitlist, but manual-reviewed or invitation allocation can replace it only before launch approval. For manual-reviewed intake, explain that application receipt is not a seat confirmation. Seats held for invitees/speakers (if counted as attendees) are explicit reservations within the same cap, never an additional hidden quota.

| Record | States / transitions |
|---|---|
| Registration | `unverified → pending → confirmed` or `waitlisted`; pending/waitlisted can become `rejected` or `withdrawn`; confirmed cancellation becomes `cancelled` |
| Ticket | `active → cancelled`; event end may mark `expired`; admission is a separate permanent record, not a destructive ticket state rewrite |
| Credential | `active → revoked/expired`; reissue creates a new version for the same ticket, never a new admission allowance |
| Delivery | `pending → processing → sent`; failure retries, then `failed`; sent means provider accepted, not necessarily inbox delivery |
| Event entry mode | `closed → online → manual → reconciling → online/closed`; changing mode requires supervisor authority and audit |
| Conditional order | `pending → paid/failed/expired/cancelled`; refund tracking separate |
| Conditional payment | `pending/succeeded/failed/unknown`; only verified provider state changes it |
| Conditional refund | `requested → approved → pending → succeeded/failed`; partial only if explicitly supported and approved |

Email-verification/action tokens are proposed to expire after 30 minutes, invitations after 24 hours. Fresh ticket viewing links may be re-requested. No business-changing action happens on GET, including when email security scanners follow links.

## Capacity and unique audience

Set `licensed_capacity = 100`, supported by S01. Organizer approves an `allocation_limit <= 100` after room capacity and counted categories are resolved (Q03). Staff/equipment physical footprint and fire-safety occupancy are separate venue constraints; a ticket counter is not a safety certification.

Define:

- `consumed`: tickets with a permanent admission record, even if holder leaves or ticket is later revoked.
- `reserved`: valid unadmitted tickets, plus unexpired paid holds if payments enabled.
- `committed = consumed + reserved`, with **committed <= allocation_limit**.

An admitted ticket never frees a place. The default proposal freezes promotions/replacements when doors open; only pre-door cancellation of an unused reservation frees inventory. Temporary exits/re-entry do not increase unique attendees or enable another person to replace someone. This responds to C08 and the current [TED attendee guidance](https://www.ted.com/tedx/organizer-guide/invite-and-engage-attendees) on limiting ticket distribution. Confirm counting categories and re-entry policy with the organizer/licence contact before coding exceptions.

### Allocation transaction

Within one database transaction: lock the event policy row; verify intake/policy, promotion cutoff and absence of a manual/reconciliation freeze; lock registration and any existing ticket; count committed inventory using indexed current records; if eligible and below cap, insert/update one active ticket and credential and enqueue delivery plus audit; otherwise retain waitlist. All allocation, hold expiry, cancellation, policy changes and roster import use the same event-row lock. Event lock first, then ticket/registration IDs in stable order. Unique constraints provide a second line of defense. At this event size, serialization on one event row is acceptable and easier to verify than multiple counters.

Do not allocate by “read count → insert” without serialization. Do not call an email or payment provider while holding database locks. Audit/outbox writes commit with the business record; job execution occurs after commit.

## QR credential and ticket delivery

Proposed QR payload: `tx1.<event-public-uuid>.<base64url-32-random-bytes>`. It is an opaque credential, not an attendee profile or a management URL. Use an operating-system cryptographic RNG; no sequential credential, name, email, phone or signed plaintext personal record. Event UUID is a namespace, not a secret. Enforce strict version, length and encoding validation. The scanner does not open arbitrary scanned URLs.

Store a unique SHA-256 digest for lookup. High entropy makes digest lookup appropriate; this is not a password-hashing design. Store the raw credential only as encrypted delivery material with a key outside the database if stable resending is required. Separate that key from backup access; do not log it. The QR image is also a bearer secret: never store it in a public bucket, analytics payload or audit diff. Render server-side/on a controlled ticket page using a tested library; no third-party QR generation API.

Ticket email includes name, approved event/date/location, booking reference, QR, assistance route and clear seat status. A short-lived management link authorizes retrieval/cancellation of that ticket only. Resend the current credential; rotate only on explicit replacement or suspected compromise. Rotation revokes old versions under the ticket lock and preserves `CheckIn` history.

Outbox workers retry the same job with a stable delivery key. A crash after provider acceptance can cause duplicate email if the provider lacks idempotency; this must not produce duplicate seats or credentials. Record provider message ID and expose unresolved delivery. Generic recovery responses and throttling prevent attendee enumeration.

## Atomic check-in transaction

Proposed endpoint: `POST /staff/events/{event_id}/check-ins`, authenticated session, CSRF, credential and client-generated request UUID. The UUID is retained across retries until outcome is known; a fresh physical scan uses a fresh request UUID. Scanner hardware label is operator context, not authentication.

Conceptual pseudocode, not implemented code:

```text
authenticate staff; verify active event-scoped check-in grant
parse QR; reject event mismatch; hash token (never log raw token)
BEGIN
  lock event row
  look up receipt by (event, actor, request_id)
  if receipt exists:
    require same digest/action fingerprint; return original receipt
  verify entry mode is ONLINE and time window permitted for a new admission
  find credential by digest and scoped event; lock its ticket
  re-read credential version/revocation and ticket state after lock
  validate ACTIVE ticket, current credential, eligibility, conditional PAID state
  if permanent CheckIn exists for ticket:
    store receipt ALREADY_ADMITTED with original time; commit
  else:
    assert ticket is an allocated reservation; committed inventory is valid
    insert CheckIn(event, ticket, actor, device, admitted_at=server_now, source)
    insert audit and receipt NEW_ADMISSION in same transaction
COMMIT
respond with receipt identifier, result, minimal attendee display, server time
```

`UNIQUE(event_id, ticket_id)` on CheckIn and `UNIQUE(event_id, actor_id, request_id)` on receipts are mandatory. Request-ID reuse with another payload returns conflict. Rejected unknown-credential receipts contain only a digest/result, not the raw token. Every ticket-state/credential writer uses the event → ticket lock order. Concurrency tests use real PostgreSQL and independent connections, not mocked locks.

Reading an existing authorized receipt remains possible during manual/closed mode so an uncertain previous outcome can be resolved; it cannot create a new admission. The UI labels it as the original result and time, not as a new entry. All ticket-affecting writes, including rotation/cancellation/import, honor the manual/reconciliation freeze; ordinary incident logging remains available.

**Guarantee:** for distinct concurrent requests, at most one committed first admission exists per allocated ticket. A retry of the same request can return the original success but is not a second admission. Cancellation/rotation/check-in serialize: whichever commits first determines the next operation's valid state. There is no distributed exactly-once guarantee for email, and no simultaneous-offline global guarantee. PostgreSQL row locks provide serialization for this proposed design ([locking documentation](https://www.postgresql.org/docs/current/explicit-locking.html)). A global SQL isolation level alone is not substituted for these lock and constraint requirements.

Staff feedback states: admitted; already admitted with original time; wrong event; invalid/revoked/cancelled; admission not open; authorization expired; pending verification; network outcome unknown. Use text/icon/sound as appropriate, not color alone. A timeout displays “Outcome unknown — retry this request,” disables the next admission confirmation until resolved, and never shows a guessed success.

## Manual search, outage and reconciliation

No-QR admission follows the same transaction after staff selects a minimally disambiguated record and records a reason. Scanner staff cannot edit the roster, allocate extra tickets or override a revoked ticket. Copying a valid QR can still cause first-presenter misuse: desk procedure compares approved minimum identity information; cryptography does not prove who holds the phone.

Offline design is a **controlled manual desk**, not cached multi-device QR verification:

1. Prepare an encrypted/physically controlled roster shortly before doors with booking references, names, validity and admitted status, export time, revision and policy version. Exclude raw credentials and unnecessary contact data.
2. Supervisor declares manual mode. If server reachable, set event mode MANUAL so every scanner is rejected. If unreachable, physically stop all scanners, including phones still on cellular data, and halt ticket changes/reissues/promotions.
3. Reconcile in-flight “unknown” outcomes before manual entry. A central desk uses one authoritative paper/local ledger and a conservative remaining-place count. If the latest roster cannot be trusted, pause admission until identity/slot state is established; do not invent an offline fraud guarantee.
4. Record booking reference, operator, actual local entry time, reason and outage epoch; no parallel independent offline desks. Keep venue physical occupancy control separately.
5. On recovery, keep mode RECONCILING. Import ledger idempotently with a stable row ID and preserve actual admission time separately from server import time. If an online CheckIn already exists, reconcile to it rather than create another. Investigate cancelled/mismatched records and count discrepancies; no blind upsert overwrites evidence.
6. Organizer/entry supervisor signs off roster and counters before ONLINE resumes. Collect and dispose of fallback copies according to retention approval.

## Conditional payments: boundary only

Gate: paid policy, lawful merchant, provider availability in Türkiye, settlement account/currency, fees, payout timing, refunds/disputes, privacy and webhook contract approved. No payment-card data enters app/database/logs. Use hosted checkout; preserve order total and currency server-side.

Provider callback redirects are display-only. Accept payment success only after signature verification over the provider-required raw request, replay controls, matching event/order/amount/currency and authoritative provider status where needed. Deduplicate by provider event ID and business transaction reference. Late success after hold expiry reacquires a slot under the allocation lock if available; otherwise mark paid-unallocated for resolution/refund, never exceed cap. Jobs reconcile missing/out-of-order notifications. Refunding is independent of cancelling a ticket, and refund failure remains pending/failed until authoritative confirmation.

Payment/refund tests in AT-18 are mandatory only when this branch is enabled. Full financial schema and provider adapter are not implemented or presumed approved by this design.

## Retention

Follow NFR-03 and Q08. Proposed credential/delivery-secret purge: 30 days after event; operational attendee retention: 90 days, subject to controller approval and justified holds. Expired QR never reactivates after restoration. Keep anonymized metrics separately. Paid financial records and speaker releases need independently approved retention; do not use the attendee default for them.
