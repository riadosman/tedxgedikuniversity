# Event platform UX audit and redesign

Audit baseline: 23 September 2026. Reviewed URL inventory, all public/staff/authentication templates, resource definitions, permissions, forms, publication snapshots, registration and admission services. Existing Chromium regression matrix passed before changes: 8 widths (320–1920), public registration/ticket/program/speaker pages, staff dashboard/settings/forms/scanner, every resource list and Arabic/Turkish direction checks. Baseline screenshots: `.local/ux-before/` (synthetic records only).

## Current product and findings

Public: home → about/theme, speakers/detail, program, venue, FAQ/contact/privacy/terms; separate attendance and volunteering; email verification → approval/allocation → private ticket and QR; recovery, cancellation, profile updates, export/erasure and volunteer withdrawal. Authentication: login, reset/change password, MFA enrollment/verification/recovery. Staff: a flat resource navigation exposing 30+ destinations, dashboard with eight equally weighted panels, generic list/detail/edit/action screens, settings, reports, imports, staff invitations, controlled roster and scanner.

Strengths: real database workflows, scoped permissions, approved publication snapshots, version checks, explicit consent, admission idempotency, QR rotation and duplicate prevention; shared templates; existing translations and responsive/accessibility tests. These are preserved.

Problems: flat navigation mirrors data models; important speaker/ticket work is buried; generic dashboard prioritizes tasks over attendance; speaker photos require disconnected upload; registration lacks a clear explanation of verification versus confirmation; ticket recovery is absent from primary event information; sorting/pagination lose filters; English confirmation dialogs bypass catalogs; language availability depends on event settings even for staff; missing active navigation; Arabic inherits Latin tight heading tracking; map action is generic; large mobile forms have unnecessary separators and padding.

Redesign: public and staff shells, overview, event information, registration guidance, attendee/ticket lists and speaker management. Improve using shared components: authentication/MFA, operational resources, reports/imports/settings and private self-service. No destructive migration, permission relaxation, replacement API or removal of resources.

## Proposed information architecture

Public navigation: Event, Speakers, Program, Venue, Register. Event information concentrates date/time/location/registration status/recovery; volunteer and supporting policy/help pages remain visible in contextual navigation/footer. Maps only link to the actual configured, confirmed venue.

Staff primary navigation (permission filtered): Overview, Attendees & tickets, QR check-in, Speakers, Event, Team & operations, Settings. Group landing pages retain every existing resource. Contextual links connect related work without a permanent 30-item sidebar. Settings contains accounts/roles, delivery/templates, privacy/audit/payments, reports and advanced configuration. Team retains departments, volunteers/applications, memberships, shifts/assignments, tasks/dependencies, incidents/runbook/contacts/files. Event retains settings, pages, schedule, talks/rehearsals, announcements and preview.

## Flows

Attendee: event facts → one registration form → email verification → existing decision/allocation → ticket/QR → maps/arrival. Closed registration explains status and offers recovery/contact; it never opens intake or promises admission. Volunteer: separately labeled application and status/recovery. Organizer: overview → contextual action → list/search/filter → details/edit/action confirmation. Speaker: basic information → save → contextual photo upload → existing scan/publication checks → publish. Check-in: camera/USB/paste credential or attendee lookup → existing server validation → unmistakable result and recent admission time; unknown outcomes keep the same-request retry.

## Original visual language

Editorial public site with TEDx red accents, warm ivory, dark charcoal, generous whitespace and a distinctive date composition. Staff uses quiet surfaces and restrained red for selection/action. System typography with Arabic-specific readable fallback, no forced Latin letter spacing in Arabic. Type scale 12/14/16/20/24/32/display; spacing 4/8/12/16/24/32/48/64; radii 8/12/20; subtle borders/shadows. Shared buttons, fields/error summaries, cards, tables, badges, disclosures, alerts and breadcrumbs. No copied branding, layouts or component code.

Responsive: 320px minimum, mobile navigation with Escape return, stacked summaries/forms, readable record cards; tablet two-column grids where space permits; desktop bounded content and persistent compact navigation. Logical CSS properties mirror RTL layout, directional decoration and alignment; email/reference/time values remain isolated LTR. Touch controls at least 44px; semantic headings/labels, visible keyboard focus, linked errors, reduced motion, no hover-only operations.

Principles consulted: [W3C form labels](https://www.w3.org/WAI/tutorials/forms/labels/) and [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary/). Applied as interaction/accessibility guidance, not copied components. Event-authored text and approved policy/speaker snapshots stay under organizer control; catalog completeness does not imply translated user content.

## Verification plan

Run Django checks, migration drift, lint, full existing business/security tests, Chromium end-to-end registration/QR tests and responsive/axe matrix; add regression coverage for group reachability, permission filtering, preserved list queries, translated confirmations and new presentation flows. Review final screenshots at desktop/mobile and Arabic RTL; verify current local site after restarting the server. Automated accessibility checks supplement visual/keyboard review and do not claim formal certification.

## Implemented and reviewed

- Seven primary staff destinations at most; every authorized legacy resource is mapped to a task group. Scanner remains directly accessible to entrance staff. Related tools and the active section remain available on child screens.
- Overview shows registrations, confirmed tickets, admissions, check-in attempts (including manual requests, deliberately not mislabeled as QR-only scans), and permission-scoped speaker totals. Five main actions at most. Operational detail remains in an expandable section that stays open across refreshes.
- Attendee/ticket tables now show registration/ticket/QR/admission state and admission time, with name/email/reference search, attendance/status filters and mobile-accessible sorting. Pagination retains the complete query. Existing CSV column contracts remain unchanged.
- Speaker cards show publication state; forms separate profile fields from administrative fields. Contextual photo upload attaches directly to a saved speaker using the existing file validation, quarantine, event scope, audited save and version checks. Stale uploads roll back both database records and new files. Existing publication permissions and scanning requirements are unchanged.
- Event facts, confirmed map link, ticket recovery, breadcrumbs, speaker navigation, registration guidance and printing are integrated. The registration screen uses the existing intake validation to explain closed windows. Destructive confirmations are translated. Download actions remain usable after a download.
- All three interface languages remain selectable. Added eleven Arabic public-content drafts; the idempotent preparation command preserves edited content and existing publication/intake state. Locally these drafts were installed, not published. Organizer-authored event text, speaker biographies and approved policies remain editable content, not automatically rewritten translations.
- Shared tokens and components cover public, staff, authentication, forms, statuses, tables and disclosures. Arabic uses logical spacing/alignment, mirrored directional decoration and explicit LTR isolation for time ranges. Camera space appears only when the camera starts, keeping mobile entrance work compact.

## Second UX review and evidence

Resolved: excessive main navigation, overloaded overview, hidden ticket recovery, disconnected speaker upload, lost filter queries, English confirmations/save/upload messages, missing Arabic event drafts, incorrect RTL time-range ordering, a tablet overflow caused by an absolutely positioned accessible label, overly tall idle scanner, and disabled repeat-download controls.

Validation recorded:

- Full regression suite: **68 passed**, including security/business workflows, admission concurrency, registration/email verification/ticket confirmation and QR decoder/idempotent retry checks.
- Following final visual refinements, affected browser and UX suites: **6 passed**. Browser matrix covers eight widths, 390/1440px in English/Turkish/Arabic, all public information pages, all resource lists and available creation forms, new task hubs, contextual photo form, menu keyboard behavior and automated axe checks on representative/public/hub flows.
- Additional targeted regressions cover preserved pagination filters and registration opening windows.
- Django system checks and migration drift clean; Ruff lint/format clean; mypy clean across 64 application files.
- Translation inventory: **731 server messages + 33 JavaScript messages**, no untranslated catalog entries in any of the three languages.
- Local public pages returned HTTP 200 in all three languages with no horizontal overflow at the reviewed mobile/desktop sizes. Synthetic screenshots: `.local/test-artifacts/design/`; actual public preview screenshots: `.local/test-artifacts/live-redesign/`.

Operational limits: the event remains subject to its existing publication/intake approvals; maps require a configured confirmed venue; photos remain quarantined until the configured scanner accepts them; email delivery and authenticator requirements are unchanged. Camera hardware/permission behavior needs a real entrance device rehearsal. Automated accessibility results are not a formal WCAG certification.
