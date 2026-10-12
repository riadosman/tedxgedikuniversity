# 04 — Functional requirements

Status: proposed acceptance contract. MVP = launch scope; Event day = required operational capability before 21 November, with manual/external delivery allowed only under [scope](03-product-scope.md) and [roadmap](11-mvp-roadmap.md). Optional and conditional paid features are not implicitly approved.

All staff workflows inherit authenticated, event-scoped, server-side authorization, input validation, CSRF protection for cookie sessions, safe error messages and auditable mutations. All timestamps are stored with timezone and displayed in Europe/Istanbul. File and export access checks apply independently of screen access. [Acceptance tests](12-acceptance-and-testing.md) provide cross-feature scenarios.

## FR-01 — Public event information

- **Description:** Public event information for the approved event scope.
- **Priority:** MVP.
- **User role:** Visitor.
- **Preconditions:** An organizer-approved content revision exists.
- **Main workflow:** Read Home, About, Speakers, Schedule, Venue, FAQ, Contact and privacy/terms pages.
- **Alternative workflows:** Unapproved speaker/room/theme uses an explicit pending label; registration closed shows closure.
- **Error states:** Unavailable revision serves last published version; broken mandatory venue/contact link blocks publication.
- **Data involved:** Event, public content, speaker profile, schedule, locale.
- **Permissions:** Anonymous sees published fields only; no directory listing or internal files.
- **Acceptance criteria:** Correct canonical name and audience hours; no invented lineup; keyboard-readable navigation; all required pages reachable.
- **Dependencies / source:** F01–F05,F08; FR-02; X01,X03; Q02,Q05

## FR-02 — Draft, approve and publish content

- **Description:** Draft, approve and publish content for the approved event scope.
- **Priority:** MVP.
- **User role:** Content Editor; Organizer.
- **Preconditions:** Staff authenticated; editor can draft; organizer can approve.
- **Main workflow:** Edit revision → validate links/branding/rights → organizer approves immutable revision → publish and invalidate cache.
- **Alternative workflows:** Rejected revision returns to draft; rollback republishes a previously approved revision.
- **Error states:** Stale revision returns conflict; unsafe HTML/URL rejected; missing approval prevents publish.
- **Data involved:** ContentRevision, approvals, public assets, audit.
- **Permissions:** Editor drafts; Organizer approves/publishes; no private document can be made public by URL edit.
- **Acceptance criteria:** Editing an approved revision invalidates approval; failed publish preserves old public version; sponsors never added to homepage.
- **Dependencies / source:** FR-12,FR-13,FR-27,FR-28; C01,C03,C06; X03

## FR-03 — Registration policy and capacity settings

- **Description:** Registration policy and capacity settings for the approved event scope.
- **Priority:** MVP.
- **User role:** Organizer.
- **Preconditions:** Q01/Q03 resolved; policy approved.
- **Main workflow:** Set opening/closing times, one general-admission type, cap and allocation mode; record approval.
- **Alternative workflows:** Close intake temporarily; lower cap only if existing commitments fit.
- **Error states:** Reject negative cap, cap above licensed ceiling, reductions below reserved/consumed places, invalid time order.
- **Data involved:** EventPolicy, capacity limit, allocation mode, registration window.
- **Permissions:** Organizer only; Event Admin can pause intake, not increase capacity.
- **Acceptance criteria:** All ticket issuance paths use same cap; dates and changes audited; no public sales before policy approval.
- **Dependencies / source:** F03; FR-13,FR-28; Q01,Q03

## FR-04 — Register and verify attendee contact

- **Description:** Register and verify attendee contact for the approved event scope.
- **Priority:** MVP.
- **User role:** Attendee.
- **Preconditions:** Registration open; approved notice displayed.
- **Main workflow:** Submit name/email, notice version and optional survey permission → generic acknowledgment → email verification → pending request.
- **Alternative workflows:** Existing address gets safe recovery path; declined survey permission does not block registration.
- **Error states:** Invalid input gives field error; throttling gives retry message; expired verification offers resend; no seat promised yet.
- **Data involved:** Attendee, registration status, verification token hash, notice receipt, consent.
- **Permissions:** Anonymous submits own request; purpose-bound token verifies only that request.
- **Acceptance criteria:** Repeated submission creates no second person/ticket for same event/email; verification is time-limited; public responses do not reveal existing status.
- **Dependencies / source:** FR-03,FR-06,FR-29; Q01,Q08

## FR-05 — Allocate seats and manage waitlist

- **Description:** Allocate seats and manage waitlist for the approved event scope.
- **Priority:** MVP.
- **User role:** Event Admin; policy worker.
- **Preconditions:** Verified eligible request; approved policy; intake/allocation open.
- **Main workflow:** Lock event capacity → inspect existing allocation → allocate atomically if permitted or place in ordered waitlist → audit → queue notice.
- **Alternative workflows:** Manual review mode requires staff acceptance; next eligible request promoted after eligible cancellation before cutoff.
- **Error states:** Cap exhausted returns waitlist, not success; duplicate request returns existing outcome; database failure rolls back.
- **Data involved:** Registration, ticket type, ticket, capacity accounting, outbox.
- **Permissions:** Event Admin approves under policy; worker cannot change eligibility rules.
- **Acceptance criteria:** 100 concurrent eligible requests cannot exceed approved cap; every confirmed registration has exactly one allocated ticket.
- **Dependencies / source:** FR-03,FR-04,FR-06; document 06 allocation transaction

## FR-06 — Issue, deliver, recover and revoke QR credentials

- **Description:** Issue, deliver, recover and revoke QR credentials for the approved event scope.
- **Priority:** MVP.
- **User role:** System; Event Admin; Attendee.
- **Preconditions:** Ticket allocated; email verified.
- **Main workflow:** Generate 32 random bytes → store digest and encrypted delivery material → create outbox job → send ticket and event details.
- **Alternative workflows:** Generic recovery request sends short-lived management link; staff reissue rotates credential under ticket lock.
- **Error states:** Email failure remains pending/failed with retry; cancelled ticket or stale credential cannot be delivered as current.
- **Data involved:** TicketCredential, delivery material, outbox, provider message metadata.
- **Permissions:** Attendee retrieves own ticket with management token; Event Admin rotates; scanner never sees management token.
- **Acceptance criteria:** QR has no PII; reissue invalidates old QR without changing admission history; retries do not create another ticket.
- **Dependencies / source:** FR-05,FR-28; document 06; Q07

## FR-07 — Cancel registration and ticket

- **Description:** Cancel registration and ticket for the approved event scope.
- **Priority:** MVP.
- **User role:** Attendee; Event Admin.
- **Preconditions:** Unexpired purpose-bound self-service authorization or staff role.
- **Main workflow:** Show cancellation consequence → explicit POST confirmation → lock event/ticket → cancel and revoke → release only eligible unused reservation → notify.
- **Alternative workflows:** Waitlist withdrawal releases no seat; repeated cancellation is idempotent; event cancellation handled by Organizer batch.
- **Error states:** Already admitted ticket cannot release its slot; expired link denied; scanned QR alone cannot cancel.
- **Data involved:** Registration, ticket, credential, audit, outbox.
- **Permissions:** Own self-service or Event Admin; event-wide cancellation Organizer only.
- **Acceptance criteria:** GET links cannot mutate; cancellation/check-in race has one serial outcome; no post-admission replacement audience.
- **Dependencies / source:** FR-05,FR-06,FR-09; Q03

## FR-08 — Controlled roster import and reconciliation

- **Description:** Controlled roster import and reconciliation for the approved event scope.
- **Priority:** MVP.
- **User role:** Event Admin.
- **Preconditions:** External roster exists; migration approved; intake paused when ownership changes.
- **Main workflow:** Upload CSV to staging → validate columns/duplicates/cap → preview → commit identified batch → audit.
- **Alternative workflows:** Invalid rows returned as safe report; rerunning committed batch returns original result.
- **Error states:** Malformed/oversized CSV rejected; no silent truncation or merge by name; conflict aborts batch.
- **Data involved:** ImportBatch, rows, external references, attendee/ticket.
- **Permissions:** Event Admin only; export permission does not confer import permission.
- **Acceptance criteria:** Dry run changes nothing; repeat import creates no duplicate; source of truth switches at a recorded cutoff.
- **Dependencies / source:** FR-03,FR-05,FR-26; Q06

## FR-09 — Authenticated QR check-in

- **Description:** Authenticated QR check-in for the approved event scope.
- **Priority:** Event day.
- **User role:** Check-in Staff.
- **Preconditions:** Event/role/device approved; server reachable; admissions enabled.
- **Main workflow:** Scan credential → parse locally → POST with request ID → server transaction validates event/status/credential and commits admission → display result.
- **Alternative workflows:** Same request retry returns original receipt; new request for used ticket shows already admitted.
- **Error states:** Wrong event, malformed, revoked, cancelled, unpaid (conditional), not open, unauthenticated and uncertain network outcomes distinguished safely.
- **Data involved:** Credential digest, ticket, CheckIn, actor, device label, idempotency receipt.
- **Permissions:** Check-in Staff for active event only; no public ticket-validation endpoint.
- **Acceptance criteria:** Two different simultaneous requests for one valid ticket yield one NEW_ADMISSION and one ALREADY_ADMITTED; no green state before commit.
- **Dependencies / source:** FR-06,FR-12,FR-13,FR-28; document 06; AT-04

## FR-10 — Manual search and exception desk

- **Description:** Manual search and exception desk for the approved event scope.
- **Priority:** Event day.
- **User role:** Check-in Staff; Event Admin.
- **Preconditions:** Authenticated staff; check-in open.
- **Main workflow:** Search name or booking reference → view minimal disambiguation → verify using agreed desk procedure → confirm → same admission transaction.
- **Alternative workflows:** Forgotten ticket uses identity confirmation; mismatched identity goes to supervisor.
- **Error states:** Ambiguous names require selection; no result or cancellation cannot be overridden by scanner; rate limit broad enumeration.
- **Data involved:** Minimal attendee identity, booking reference, admission state, reason.
- **Permissions:** Scanner sees masked email; Event Admin can resolve identity disputes; neither bypasses cap.
- **Acceptance criteria:** No direct check-in flag editing; manual admission records actor, reason and request ID; names alone do not auto-admit.
- **Dependencies / source:** FR-09; Q03,Q08

## FR-11 — Network outage and manual fallback

- **Description:** Network outage and manual fallback for the approved event scope.
- **Priority:** Event day.
- **User role:** Event Admin; designated desk operator.
- **Preconditions:** Rehearsed plan and protected recent roster available.
- **Main workflow:** Declare manual mode → pause digital admission and ticket-affecting writes → reconcile uncertain requests → single desk records admissions with time/actor → reconcile before reopening online.
- **Alternative workflows:** Backup connectivity may restore service; unknown credentials wait for supervisor.
- **Error states:** Stale roster, lost log or competing offline desks triggers pause; no client claims offline global validation.
- **Data involved:** Versioned roster, outage epoch, manual ledger, reconciled CheckIn records.
- **Permissions:** Only Event Admin changes mode; appointed operator holds roster; no general volunteer export.
- **Acceptance criteria:** Rehearsal accounts for every entry with no extra seat; server rejects scanners during declared manual mode; offline guarantee limitations are visible.
- **Dependencies / source:** FR-09,FR-10,FR-26,FR-30; document 06

## FR-12 — Staff authentication and recovery

- **Description:** Staff authentication and recovery for the approved event scope.
- **Priority:** MVP.
- **User role:** Invited staff; Organizer.
- **Preconditions:** Chosen authentication configuration; approved role holder.
- **Main workflow:** Accept expiring invitation → enroll authentication/MFA as required → login → event-scoped session → logout.
- **Alternative workflows:** Recover via verified account process; Organizer revokes lost-device sessions.
- **Error states:** Expired invitation, invalid credentials, throttling and inactive membership denied without account enumeration.
- **Data involved:** User, external identity or password hash, session, invitation, MFA metadata.
- **Permissions:** No open staff signup; no shared account; technical service accounts cannot browse staff UI.
- **Acceptance criteria:** Unauthenticated mutation rejected; session revoked after suspension; sensitive action requires recent reauthentication.
- **Dependencies / source:** FR-13; Q04,Q07; NFR-01

## FR-13 — Role grants and scope enforcement

- **Description:** Role grants and scope enforcement for the approved event scope.
- **Priority:** MVP.
- **User role:** Organizer.
- **Preconditions:** Authenticated organizer with recent MFA; target identity verified.
- **Main workflow:** Grant predefined role at event/department scope → record actor/reason → invalidate access cache.
- **Alternative workflows:** Remove grant; assign separate scoped roles; maintain backup organizer.
- **Error states:** Self-promotion, invalid department, cross-event object and removing last active organizer rejected.
- **Data involved:** RoleGrant, membership, audit.
- **Permissions:** Organizer grants business roles; technology role alone cannot grant itself content/attendee access.
- **Acceptance criteria:** Every endpoint/download/export checks object scope server-side; revoked grant ceases authorizing within 60 seconds.
- **Dependencies / source:** document 05; FR-12,FR-28

## FR-14 — Volunteer application

- **Description:** Volunteer application for the approved event scope.
- **Priority:** Optional.
- **User role:** Volunteer applicant.
- **Preconditions:** Recruitment approved and notice live.
- **Main workflow:** Submit name, email, availability, relevant skills and department preference → acknowledgment.
- **Alternative workflows:** Withdraw own application; existing applicant updates through verified access.
- **Error states:** Closed intake, invalid availability, repeated submission or oversized text handled without duplicate.
- **Data involved:** VolunteerApplication, notice receipt, optional contact.
- **Permissions:** Applicant own data; authorized reviewers only; no public applicant list.
- **Acceptance criteria:** No CV/ID upload required; application does not create staff permissions or acceptance.
- **Dependencies / source:** FR-12,FR-29; Q10; document 07

## FR-15 — Volunteer review and acceptance

- **Description:** Volunteer review and acceptance for the approved event scope.
- **Priority:** Event day if recruiting.
- **User role:** Event Admin; Department Leader.
- **Preconditions:** Application available; reviewer scoped.
- **Main workflow:** Review → record recommendation → Event Admin accepts/rejects → invite accepted volunteer if account needed.
- **Alternative workflows:** Waitlist, withdrawal and reassignment preserve history.
- **Error states:** Acceptance without capacity/supervisor decision or duplicate active membership flagged; email failure does not revert review.
- **Data involved:** Application status, review note, volunteer profile, invitation.
- **Permissions:** Leader recommends for own department; Event Admin finalizes; private review notes not visible to applicants.
- **Acceptance criteria:** Acceptance and role assignment are separate actions; rejected application cannot access internal dashboard.
- **Dependencies / source:** FR-14,FR-16,FR-28

## FR-16 — Departments, leaders and volunteer assignments

- **Description:** Departments, leaders and volunteer assignments for the approved event scope.
- **Priority:** Event day.
- **User role:** Organizer; Event Admin.
- **Preconditions:** Named organizational model approved.
- **Main workflow:** Create small department set → organizer appoints scoped leaders → Event Admin assigns accepted volunteers.
- **Alternative workflows:** Member can have approved multiple memberships; archive department only after reassignment.
- **Error states:** Cross-event membership, orphan active tasks or unauthorized leader change rejected.
- **Data involved:** Department, membership, RoleGrant, supervisor.
- **Permissions:** Organizer appoints leaders; Event Admin memberships; leaders cannot expand own scope.
- **Acceptance criteria:** Each active volunteer has supervisor/contact route; moving department immediately changes access.
- **Dependencies / source:** FR-13,FR-15; Q04; document 07

## FR-17 — Shifts, briefing and volunteer attendance

- **Description:** Shifts, briefing and volunteer attendance for the approved event scope.
- **Priority:** Event day.
- **User role:** Leader; Volunteer.
- **Preconditions:** Approved membership and event-day role.
- **Main workflow:** Leader assigns time/location → volunteer acknowledges → leader records briefing/training and arrival.
- **Alternative workflows:** Absence escalates; replacement checked for briefing; printed roster allowed.
- **Error states:** Overlapping active shifts, outside allowed access hours or untrained scanner assignment rejected/flagged for supervisor.
- **Data involved:** Shift, assignment, briefing status, arrival timestamp.
- **Permissions:** Leader edits own department; volunteer sees/acknowledges own record.
- **Acceptance criteria:** Attendance of a volunteer is separate from an attendee CheckIn; no automatic public ticket consumed.
- **Dependencies / source:** FR-16; Q03,Q09; document 07

## FR-18 — Department leader dashboard

- **Description:** Department leader dashboard for the approved event scope.
- **Priority:** Event day.
- **User role:** Department Leader.
- **Preconditions:** Active scoped grant.
- **Main workflow:** View own members, readiness, shifts and tasks → assign eligible team member → escalate blocker.
- **Alternative workflows:** Cross-department dependency shows task title/status only if shared.
- **Error states:** Foreign department identifiers return denied/not found; stale change returns conflict.
- **Data involved:** Scoped roster, assignments, tasks, non-sensitive incidents.
- **Permissions:** Own department only; no applicant private notes unless reviewer.
- **Acceptance criteria:** Totals cannot reveal hidden departments; task assignment to foreign member rejected server-side.
- **Dependencies / source:** FR-13,FR-16,FR-17,FR-19

## FR-19 — Tasks, dependencies and readiness evidence

- **Description:** Tasks, dependencies and readiness evidence for the approved event scope.
- **Priority:** Event day.
- **User role:** Leader; Volunteer; Event Admin.
- **Preconditions:** Owner and department exist.
- **Main workflow:** Create task with deadline/owner → add dependencies → update state → attach completion evidence.
- **Alternative workflows:** Block task with reason/escalation; reopen with note.
- **Error states:** Dependency cycles/self-links, missing owner, foreign department edit and stale version rejected.
- **Data involved:** Task, TaskDependency, evidence reference, activity.
- **Permissions:** Leader manages own tasks; assignee updates own work; Event Admin oversees.
- **Acceptance criteria:** Critical task cannot be marked complete without evidence; deadline views use event timezone.
- **Dependencies / source:** FR-13,FR-27,FR-28; F14

## FR-20 — Versioned operational runbook

- **Description:** Versioned operational runbook for the approved event scope.
- **Priority:** Event day.
- **User role:** Program/production lead; Organizer.
- **Preconditions:** Approved program timings and role holders.
- **Main workflow:** Draft cue entries with times, actor and technical needs → validate → organizer publishes → distribute versioned local copy.
- **Alternative workflows:** Emergency change requires named authorizer and staff acknowledgment.
- **Error states:** Overlap, invalid duration, missing cue owner and stale revision prevent routine approval.
- **Data involved:** RunbookRevision, entries, acknowledgments.
- **Permissions:** Leads draft; Organizer approves; volunteers view designated operational subset.
- **Acceptance criteria:** Public pages never expose private cue notes/contact list; latest revision and printed timestamp visible.
- **Dependencies / source:** FR-19,FR-24,FR-27; C04,C05

## FR-21 — Incident capture and escalation

- **Description:** Incident capture and escalation for the approved event scope.
- **Priority:** Event day.
- **User role:** Staff; Event Admin.
- **Preconditions:** Staff authenticated; emergency contact procedure exists.
- **Main workflow:** Record non-medical operational summary, severity, location → assign owner → escalate → resolve with action.
- **Alternative workflows:** During emergency use direct help first and log later; offline paper log reconciled.
- **Error states:** No network shows fallback; unnecessary health/identity details rejected by policy and removed through controlled correction.
- **Data involved:** Incident, actor, owner, status, timestamps, restricted note.
- **Permissions:** Staff creates; leader sees own/shared incidents; Event Admin restricted overview.
- **Acceptance criteria:** Critical incident stays visible until acknowledged; no automatic claim emergency services were notified.
- **Dependencies / source:** FR-13,FR-28; Q02

## FR-22 — Operational announcements

- **Description:** Operational announcements for the approved event scope.
- **Priority:** Event day.
- **User role:** Event Admin; Organizer.
- **Preconditions:** Approved audience and message.
- **Main workflow:** Draft → preview audience → publish in-app notice → record acknowledgment for critical updates.
- **Alternative workflows:** Scheduled notice; local briefing if devices unavailable.
- **Error states:** Unauthorized cross-scope message, expired schedule or delivery failure flagged.
- **Data involved:** Announcement, audience scope, acknowledgment, optional outbox.
- **Permissions:** Event Admin operational notices; Organizer public event changes.
- **Acceptance criteria:** No bulk personal-address exposure; push/email is not assumed delivered because queued.
- **Dependencies / source:** FR-13,FR-20,FR-28

## FR-23 — Speaker and talk preparation

- **Description:** Speaker and talk preparation for the approved event scope.
- **Priority:** Event day.
- **User role:** Speaker Manager; Organizer.
- **Preconditions:** Candidate information collected through approved process.
- **Main workflow:** Record idea → outline → draft → fact/rights review → timed rehearsal → technical check → organizer approves specific version.
- **Alternative workflows:** Request changes; reserve talk follows identical review; external document links allowed.
- **Error states:** Missing release/rights, unresolved claims or duration above event policy blocks readiness.
- **Data involved:** Speaker, Talk, checklist/review evidence, rehearsal, private document.
- **Permissions:** Speaker Manager edits private workflow; Organizer final approval; no default speaker account.
- **Acceptance criteria:** Public biography approval is independent of internal readiness; edits to reviewed script invalidate readiness.
- **Dependencies / source:** FR-02,FR-27,FR-28; F09,F10,F13

## FR-24 — Public schedule and talk allocation

- **Description:** Public schedule and talk allocation for the approved event scope.
- **Priority:** MVP.
- **User role:** Speaker Manager; Organizer.
- **Preconditions:** Public content policy and time window approved.
- **Main workflow:** Draft sessions → validate durations/transitions → approve revision → publish public subset.
- **Alternative workflows:** Unconfirmed lineup shown as pending; cancellation requires new revision.
- **Error states:** Overlapping slots, end after 16:00 or unapproved public speaker blocked.
- **Data involved:** ScheduleItem, talk, locale, published revision.
- **Permissions:** Program drafts; Organizer publishes; internal cue fields excluded.
- **Acceptance criteria:** Server validates full 180-minute window constraints; public timetable uses approved audience times.
- **Dependencies / source:** FR-02,FR-23; F04; C04,C05

## FR-25 — Administrative event dashboard

- **Description:** Administrative event dashboard for the approved event scope.
- **Priority:** MVP.
- **User role:** Organizer; Event Admin.
- **Preconditions:** Role-scoped queries available.
- **Main workflow:** Show allocated, pending, waitlisted, cancelled, ever-admitted and failed-delivery counts with timestamp.
- **Alternative workflows:** Event-day view adds unresolved incidents/readiness; unavailable data shows unavailable.
- **Error states:** Stale or failed query never displays zero or invented percentage.
- **Data involved:** Aggregate registration/ticket/check-in/outbox/task states.
- **Permissions:** Organizer/Event Admin full operational counts; other roles scoped projections.
- **Acceptance criteria:** Ever-admitted is labelled separately from occupancy; totals reconcile to transactional roster.
- **Dependencies / source:** FR-05,FR-09,FR-19,FR-21

## FR-26 — Exports and operational reports

- **Description:** Exports and operational reports for the approved event scope.
- **Priority:** MVP.
- **User role:** Authorized export holder.
- **Preconditions:** Role, purpose and approved columns specified.
- **Main workflow:** Choose approved export → log purpose → generate CSV/local runbook → deliver short-lived private download.
- **Alternative workflows:** Privacy-approved survey subset; anonymized final metrics; suppressed unsafe cells.
- **Error states:** Foreign scope, unknown column or expired download denied; oversized export fails safely.
- **Data involved:** ExportJob, redacted rows, audit, manifest/version.
- **Permissions:** Organizer authorizes broad export; Event Admin roster only; other roles limited in document 05.
- **Acceptance criteria:** CSV formula injection neutralized; QR secrets absent; email list never public; exported record count and timestamp included.
- **Dependencies / source:** FR-13,FR-28,FR-29; X04

## FR-27 — Private documents and approved public assets

- **Description:** Private documents and approved public assets for the approved event scope.
- **Priority:** Event day; public assets MVP.
- **User role:** Speaker Manager; Leader; Content Editor.
- **Preconditions:** Storage configuration approved; uploader authorized.
- **Main workflow:** Upload allowlisted file → size/type validation and malware quarantine → assign scope/version → authorize download.
- **Alternative workflows:** External approved storage reference instead of upload; replace creates new version.
- **Error states:** Oversize, executable, MIME mismatch, malicious file, cross-scope link or expired URL denied.
- **Data involved:** File metadata, checksum, storage key, linked entity, classification.
- **Permissions:** Public conversion requires publisher approval; internal evidence downloads check role each time.
- **Acceptance criteria:** No public bucket for private files; raw HTML/SVG not accepted without separate safe pipeline; orphan files purged by retention job.
- **Dependencies / source:** FR-02,FR-13; NFR-04

## FR-28 — Audit log and change history

- **Description:** Audit log and change history for the approved event scope.
- **Priority:** MVP.
- **User role:** System; Organizer.
- **Preconditions:** Authenticated mutation or automated actor context.
- **Main workflow:** Record actor, event, action, target, safe change summary, result and request ID in transaction.
- **Alternative workflows:** Anonymous registration uses system/request identity without copying form body; failed authorization logged separately.
- **Error states:** Audit insert failure rolls back business mutation; denied request must not disclose record existence.
- **Data involved:** AuditLog; no raw QR/session/payment secrets.
- **Permissions:** Application role can append, not edit/delete; Organizer reads approved audit reports.
- **Acceptance criteria:** Ticket, grant, publication, export and mode changes traceable; infrastructure admin bypass is documented, not falsely impossible.
- **Dependencies / source:** FR-13; NFR-02

## FR-29 — Privacy notice, rights and retention

- **Description:** Privacy notice, rights and retention for the approved event scope.
- **Priority:** MVP.
- **User role:** Attendee; privacy owner; Organizer.
- **Preconditions:** Controller, purposes, recipients and retention approved.
- **Main workflow:** Present versioned notice → record appropriate acknowledgments/optional permissions → process verified access/correction/deletion requests → execute approved retention.
- **Alternative workflows:** Withdraw survey consent without cancelling ticket; lawful hold records reason and expiry.
- **Error states:** Unverified requester, blanket deletion of protected accounting evidence or unapproved export rejected.
- **Data involved:** NoticeReceipt, Consent, PrivacyRequest, retention policy.
- **Permissions:** Privacy owner explicitly granted restricted role; no blanket university access.
- **Acceptance criteria:** Optional consent not preselected; erase/anonymize across database, files, jobs and exports per schedule; backup expiry addressed.
- **Dependencies / source:** FR-26,FR-28; Q08; X07,X08

## FR-30 — Health, backups and recovery operations

- **Description:** Health, backups and recovery operations for the approved event scope.
- **Priority:** MVP foundation; event-day rehearsal.
- **User role:** Technology Lead.
- **Preconditions:** Approved deployment accounts and backup destination.
- **Main workflow:** Monitor synthetic health/queue/database → alert assigned operator → restore tested backup if needed → reconcile ledger → reopen after validation.
- **Alternative workflows:** Use standby device/network or manual mode; rollback application against compatible schema.
- **Error states:** Restore without identity/capacity/ledger reconciliation cannot resume admissions.
- **Data involved:** Health metadata, backup manifest, recovery log, incident.
- **Permissions:** Technology Lead executes; Organizer authorizes operational reopening; credentials outside repository.
- **Acceptance criteria:** Meet NFR-06 recovery targets in rehearsal; stale backup never silently loses a known admission.
- **Dependencies / source:** FR-11,FR-28; Q07,Q09

## FR-31 — Hosted payment lifecycle (conditional)

- **Description:** Hosted payment lifecycle (conditional) for the approved event scope.
- **Priority:** Phase 2 / paid gate.
- **User role:** Attendee; Finance; provider worker.
- **Preconditions:** Paid policy, merchant, provider, terms and amount/currency approved.
- **Main workflow:** Reserve expiring place → hosted checkout → verify signed provider notification/status → idempotently mark paid → allocate/issue atomically.
- **Alternative workflows:** Delayed success after expiry goes to reconciliation/refund without overbooking; out-of-order event resolved from provider status.
- **Error states:** Invalid signature, mismatched amount/currency/order, replay, uncertain status or failed payment issues no ticket.
- **Data involved:** Order, PaymentAttempt, PaymentEvent, reservation, outbox; no card data.
- **Permissions:** Finance reads minimal financial data; only verified server process marks paid.
- **Acceptance criteria:** Client redirect cannot confirm payment; webhook retries yield one financial effect and one ticket at most.
- **Dependencies / source:** FR-03,FR-05,FR-06; Q12; document 06

## FR-32 — Refund and settlement reconciliation (conditional)

- **Description:** Refund and settlement reconciliation (conditional) for the approved event scope.
- **Priority:** Phase 2 / paid gate.
- **User role:** Finance; Organizer.
- **Preconditions:** Approved provider/refund policy and refundable transaction.
- **Main workflow:** Preview amount → authorized approval → provider request with idempotency key → reconcile verified outcome → notify.
- **Alternative workflows:** Partial refund only if approved policy supports it; provider timeout stays pending; dispute handled manually.
- **Error states:** Repeated request cannot refund twice; failed refund not labelled complete; attended ticket never frees audience allocation.
- **Data involved:** Refund, provider references, order balances, audit.
- **Permissions:** Finance requests; Organizer approves refund; no payment-card access.
- **Acceptance criteria:** Refund state independent of ticket/admission state; settled totals reconcile against provider report.
- **Dependencies / source:** FR-31,FR-07,FR-28; Q12

## FR-33 — Post-event closeout and official tool handoff

- **Description:** Post-event closeout and official tool handoff for the approved event scope.
- **Priority:** Event day planning / post-event execution.
- **User role:** Organizer; Speaker Manager; Event Admin.
- **Preconditions:** Event ended; permission/rights records reviewed.
- **Main workflow:** Prepare permitted survey export → organizer uses official tool → review media → record upload references → aggregate report and retention handoff.
- **Alternative workflows:** Failed external upload remains pending; withdrawn permission excluded; restricted media not published.
- **Error states:** Missing release, incorrect event metadata or unapproved recipient transfer blocks handoff.
- **Data involved:** Closeout tasks, approved exports, media references, aggregate metrics.
- **Permissions:** Organizer external account; role-limited document preparation.
- **Acceptance criteria:** No undocumented TED API calls or copied login credentials; actual completion proof attached; deadlines tracked.
- **Dependencies / source:** FR-23,FR-26,FR-29; F19; X04,X05

## FR-34 — Exit/re-entry and audience accounting

- **Description:** Exit/re-entry and audience accounting for the approved event scope.
- **Priority:** Event day.
- **User role:** Check-in Staff; Event Admin.
- **Preconditions:** Q03 policy approved; individual already admitted.
- **Main workflow:** Record departure if occupancy tracking enabled → supervised re-entry of same person under approved policy.
- **Alternative workflows:** If digital exit tracking not adopted, venue uses separate physical tally and dashboard states occupancy unavailable.
- **Error states:** Different person using vacated slot denied; negative occupancy and re-entry without previous admission rejected.
- **Data involved:** Admission/exit ledger if approved; permanent ever-admitted record.
- **Permissions:** Scanner logs movement only when enabled; supervisor resolves disputes.
- **Acceptance criteria:** Checkout never deletes first CheckIn or releases allocation; unique admitted population never exceeds ceiling.
- **Dependencies / source:** FR-09,FR-11,FR-25; C08; Q03

