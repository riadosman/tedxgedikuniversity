# Organizer onboarding

Infrastructure operator prepares the site and runs `python manage.py bootstrap_organizer YOUR_USERNAME YOUR_EMAIL` using your chosen identity. Enter the password privately at the hidden prompt. There is no default administrator password. You do not need to administer Django or PostgreSQL yourself.

1. Open the supplied HTTPS site → Team sign in. Set up your authenticator, scan its private enrollment QR, enter the current code and store one-use recovery codes privately. Never share the account or QR.
2. Event settings: review imported identity/date/licence ceiling; confirm room, public hours, separate entrance opening, contact, capacity allocation, languages, registration window and versioned privacy/policy text. Nothing opens or publishes automatically. Paid registration remains unavailable without its separate integration.
3. Team accounts → Invite staff member. Each person sets a password from their private link. Roles & permissions → explicitly grant the appropriate event role. Accounts alone provide no event access. Require each staff member's MFA. Keep a responsible non-expiring organizer.
4. Add Departments with responsibilities/readiness. Assign each Department Leader role to its department. Add memberships/supervisors; leaders cannot administer other departments.
5. Configure immediate registration, dates, free admission, capacity and an approved versioned privacy notice. Enable the general admission category. The public form collects only name, email and notice acknowledgement; a valid submission immediately creates a ticket when capacity is available. See the [ticketing guide](immediate-ticketing.md). No attendee email verification or staff approval is required.
6. Email is optional for attendee tickets. If enabled, the operator configures the existing email worker/scheduler. Review templates for every enabled language and check staging delivery. Staff invitations still need their existing communication setup.
7. Public pages & FAQs: maintain approved text per language, save drafts and explicitly publish reviewed revisions. Preview the site. Branding, event translations, privacy and terms need their own approval; translated interface controls do not approve event content.
8. Add Speakers, private notes and public biography/photo separately. Record consent/confirmation. Add talks, release/fact/rights checks, technical needs and rehearsals. Approve ready talks, publish speakers, then create/publish program items. Production cues remain private.
9. Review Volunteer applications. Acceptance does not grant privileges: invite accounts, grant roles, link profiles to users, assign departments/shifts, record briefing and collect acknowledgments.
10. Add Tasks with owner, deadline, priority and completion criteria; then dependencies, comments and files. Quarantined attachments require configured malware scanning.
11. Add Operational contacts, emergency procedures and Runbook items. Review audience before publishing. Assign incident escalation and targeted announcements. Avoid unnecessary personal/medical details.
12. Rehearse actual devices/staff, reports, controlled roster custody and backup recovery. Only organizer opens admission mode after the final gate. Check-in staff cannot override capacity, policy or duplicate checks.

For errors preserve a nonsecret request ID and report an incident to the technology lead. Never paste credentials/private ticket links into shared chats. Use the [entrance procedure](../event-day/check-in-procedure.md) and [runbook](../event-day/runbook.md).
