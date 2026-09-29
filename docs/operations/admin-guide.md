# Organizer and staff guide

## Getting ready

Set the actual admission opening time separately from team setup time before enabling online entry. The imported 18-minute talk ceiling comes from source correspondence; audience capacity remains bounded by the imported licence ceiling. Enable the general admission category in Ticket types for immediate public registration. Every currently supported category counts toward capacity; staff-only/non-counted admission needs a separately approved policy.

Uploaded files remain quarantined until a configured scanner passes them. An infrastructure operator can run `python manage.py scan_documents --limit 25` after configuring `FILE_SCAN_COMMAND`. The command verifies stored checksums and audits its decisions; timeouts or unavailable files remain quarantined. It does not substitute for a real malware scanner.

Sign in with your assigned account, enroll an authenticator and privately store recovery codes. Accounts and event roles are separate. The organizer manages Team accounts and Roles & permissions. Department leaders require a department-scoped grant. Revoked or expired grants stop authorizing requests immediately. Ordinary users cannot edit audit or admission history.

Event settings control publication, dates, capacity, intake mode, application window, privacy notice/version, recruitment and policy approvals. The licence ceiling comes from the source import; operational capacity must not exceed it. Registration starts closed, payment mode undecided and general ticket type disabled. Before launch, approve the actual free/paid decision, capacity, versioned notice and dates. Paid mode cannot be opened without a completed provider integration.

## Content and speakers

Edit page drafts by key/language. Use About, Theme, FAQ and other page keys for event copy. Publish the reviewed revision as organizer; later draft edits do not replace the public snapshot. Never paste private correspondence or meeting credentials into public content.

Speaker records separate biography/publication consent from private contact and preparation notes. A public speaker needs confirmed status and publication consent. Talk preparation records track release, fact check, rights and technical requirements. Final talk approval is an organizer action. Public schedule items require approved talks and published speakers. Production cues remain private. Rehearsals and shifts enforce positive durations; public sessions must fit the event window without overlap.

Upload PDF/PPTX/JPEG/PNG files of at most 25 MB into the correct scope. Files remain quarantined without a configured malware scanner. Downloading requires current object authorization. Public speaker photos require a clean public-candidate image and explicit speaker publication. Archiving removes ordinary access; erasure is a separate retention decision.

## Attendees and tickets

See the [ticketing operating guide](immediate-ticketing.md) for the complete setup and migration instructions. Attendees submit only name, email and a required acknowledgement of the versioned privacy notice. Tickets are issued immediately within the capacity transaction; email verification and staff approval are no longer required. Duplicate email submissions display an already-registered message without revealing ticket details. Full events reject registration.

Search tickets by name, email or public ticket ID. Correct attendee records with a reason after identity review. Cancel and rotate credentials using the ticket actions, never direct database edits. Rotation preserves admission history. Attendees can print/save their private ticket, correct their name, download their data, cancel or request erasure. Email recovery is optional; tickets remain valid without email delivery.

Registration imports and invitation creation are retired; historical records are preserved. Controlled entrance-ledger imports remain available. Authorized administrators can export ticket details without QR secrets and use the checked-in attendee email export for the manual TEDx post-event uploader process.

## Volunteers and departments

Recruitment is separately opened after notice approval. Review/interview/waitlist/accept/reject applications. Acceptance creates a volunteer profile but no privileges. Invite the volunteer account and assign a volunteer role separately, then connect that account to the profile. Assign memberships, supervisor, shifts and tasks. A shift assignment requires active membership and rejects overlapping shifts. Volunteers acknowledge their own shift; leaders/admins record briefing and arrival.

## Tasks, incidents and announcements

Every task has acceptance text; owners, departments, priority and deadlines are explicit. Dependencies cannot form cycles. A task cannot complete while prerequisites are incomplete. Volunteers submit assigned work for review; leaders approve only within their own department. Stale form edits are rejected rather than overwriting newer work.

Report incidents with severity, category and owner. Record a resolution before closing. Critical safety issues require the venue's immediate escalation procedure; the application is a record and coordination tool, not an emergency responder. Publish runbook snapshots for the appropriate staff/department/leadership audience.

Announcements target staff, leaders, departments, volunteers, check-in staff, speakers or organizers. Publication queues operational emails to the selected active staff accounts; future publication time delays delivery. Staff can record read state. Reports and CSV exports require the corresponding permission and a purpose. Exports contain minimum columns and neutralize spreadsheet formulas.

## Privacy and closeout

Verify requester identity before changing a privacy request to verified. Erasure respects the configured event retention period and any active hold. Anonymization preserves ticket/admission integrity while removing attendee identity, answers, credentials and matching outbox material. User free-text notes and external copies require a separate documented review. Backup expiry and restored-data suppression are part of the operator's retention process; changing the live database does not erase downloaded files or historical backups.
