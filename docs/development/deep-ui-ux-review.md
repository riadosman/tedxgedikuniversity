# Product experience review — September 2026

## Audit evidence and scope

The audit used Chromium through Python Playwright because the in-app browser runtime was not exposed in this session. The public local preview was inspected without changing event data. Organizer, registration, ticket and admission screens used synthetic records in pytest's isolated PostgreSQL database. No production attendee data, publication status or intake settings were changed.

The initial walkthrough covered all public destinations, every permission-visible resource list and editable form, the workspace groups, event settings, reports, account screens, speaker photo upload, ticket detail and check-in. It followed actual navigation links as well as visiting routes. Original visual contact sheets remain in `../../.local/deep-ux/before/gallery-*.png`; the initial public screenshots are in `../../.local/deep-ux/before-public/`. Individual files under `before/` also contain an intermediate redesign pass; the original contact sheets are the before evidence.

## Findings and design decisions

| Finding | Product change |
| --- | --- |
| Oversized decorative date competed with the event identity; venue and ticket information were scattered | Editorial hero with a single booking panel containing date, time, venue, maps, registration and ticket recovery |
| About page was a prose endpoint with little reason to continue | Event hub assembles approved speaker and program snapshots, venue information and booking actions |
| A separate language toolbar consumed space on every screen | Compact keyboard-operable language disclosure in the header; all three languages remain available |
| Arabic used a system fallback with inconsistent weight and rhythm | Self-hosted Noto Sans Arabic; Manrope for Turkish/English; separate Arabic heading rhythm and logical geometry |
| Short forms floated halfway down the workspace because the grid item used vertical auto margins | Workspace consistently starts at the top; narrower forms use a readable content measure |
| Attendees required an intermediate hub; eight peer links were permanently exposed | Direct attendee destination, three main tabs, remaining tools in a contextual disclosure |
| Status, email, QR and check-in competed as separate table columns | Four-column people/ticket table; secondary data grouped under identity or status; all details and export fields retained |
| Dashboard looked healthy despite pending registration decisions | Permission-scoped pending review count and a direct filtered action in the attention panel |
| Settings presented multiple long forms simultaneously | Six labeled disclosure sections, first open, invalid-field and guide links open/focus their target |
| Speaker photo instructions dominated the profile form | Optional contextual instructions below profile fields; existing direct upload flow and publication checks retained |
| Closed intake used the same green treatment as success | Distinct warning state; registration steps shown only when intake is available |
| Destructive ticket actions used a browser-native prompt | Shared semantic modal with explicit action, safe back button, Escape support and native focus containment |
| Three competing CSS layers made consistency fragile | Replaced component CSS with one shared system plus tokens; removed the obsolete product override sheet |

## Information architecture

Public: Home → Event hub → Registration. Speakers, program and venue remain direct destinations. Ticket recovery, volunteer registration, contact and policy information remain available.

Organizer: Overview, QR check-in, Attendees & tickets, Speakers, Event. Team operations and Settings form a lower-priority group. Attendance has three daily tabs (attendees, registrations, tickets), with invitations, admission history, ticket types and imports/roster under More tools. Permission-filtered links and existing routes remain intact.

## Design system

- Typography: Manrope and Noto Sans Arabic, locally served; body 15px, body line-height 1.65/Arabic 1.8, controlled responsive display/headings. Font licenses are stored beside font files.
- Neutral canvas, white surfaces, restrained red primary action. Success, warning and error have semantic colors and text labels.
- Spacing based on 4/8/12/16/24/32/48/64px values; 8px controls and 10–12px panels.
- 44px primary controls, explicit labels, visible focus, reduced-motion support, accessible dialog and live status feedback.
- Public content bounded at 1240px; workspace sidebar 225px. Layout transitions at 1100/850/700px; mobile tables become labeled records rather than squeezed columns.
- Shared booking, speaker, program, form-field and people-table templates prevent page-specific reinvention.

## Boundaries

No migrations, database schema, authentication, permission rules, API contracts, registration decisions, QR validation or ticket business logic changed. View changes comprise read-only presentation queries for approved event content and permission-scoped pending registrations, plus translated page titles. Form changes translate labels and choice captions without changing submitted values or validation. Synthetic names, dates and content in the test atlas are fixtures, not real event announcements. The real event remains an unpublished local preview with registration closed until its existing readiness requirements are met.

## Reproducible QA

`tests/test_product_review.py` captures all routes at 1440, 1280, 1024, 390 and 360px in Arabic, Turkish and English. It checks HTTP responses, document overflow, JavaScript errors and primary-screen WCAG rules, and exercises language switching, confirmation dismissal, empty search, validation, closed intake, recovery success and denied camera access. `tests/test_design_browser.py` retains the wider existing responsive matrix and guide/focus checks. `tests/test_browser.py` retains the registration-to-ticket-to-admission rehearsal, duplicate scan and uncertain-network-outcome checks.

## Final results — 23 September 2026

- The complete browser atlas passed: 90 routes × three languages × five widths = 1,350 route captures, plus 120 interaction-state captures. It followed 45 navigation destinations. No route overflow or JavaScript errors were detected. Automated accessibility checks passed on the principal screens at 390 and 1440px; this is not a formal accessibility certification.
- Manual image review covered the desktop route contact sheets in all three languages, Arabic mobile sheets, Turkish mobile samples, and full-resolution principal screens across the requested widths. This visual review found issues that passing tests had missed: primary CTA placement, an overlapping sticky save bar, excessively tall photo placeholders, untranslated page titles and boolean values, incorrect back-arrow direction, and misleading green informational notices. These were corrected.
- The final correction pass passed independently: 13 affected routes × 15 combinations = 195 route captures, plus 120 state captures. Updated images replace the corresponding images in the final atlas; both inventories remain available. Recovery success is asserted explicitly, with rate buckets reset only in the isolated test database between independent viewport journeys.
- Regression run: **72 passed, one failed**. The remaining failure is the existing admission performance threshold: 100 requests over 10 seconds, five clients, 100 successful admissions, p95 **619.89ms** versus the required **500ms**, p99 **631.32ms**. Earlier shorter runs also exceeded p95. This is an unresolved local performance result; thresholds and backend admission logic were not changed to conceal it. The visual audit is a separate passing test, making 73 distinct passing tests overall and one outstanding performance test.
- Ruff lint and formatting passed (121 files); mypy passed (64 source modules); Django system checks passed; migration drift check reported no changes.
- Translation inventory: 742 server messages and 34 JavaScript messages per language, with no untranslated catalog entries. User-authored event, speaker and schedule content remains authored content, not automatically translated text.
- The restarted real localhost preview passed a read-only final check: 30 homepage captures (full-page and viewport at all 15 combinations) and 15 linked public pages. All staff mutations and registration/admission rehearsals used synthetic isolated test records.

### Evidence and limits

- [Filterable final screenshot gallery](../../.local/deep-ux/index.html) — 1,470 full-resolution screenshots; filter by language, width and page.
- [Full atlas inventory](../../.local/deep-ux/final/inventory.json), [correction inventory](../../.local/deep-ux/fixes/inventory.json), [performance result](../../.local/test-artifacts/load-10s.json).
- Original baseline public screenshots remain in `.local/deep-ux/before-public`; original baseline contact sheets remain in `.local/deep-ux/before/gallery-*.png`. Individual images in the latter directory were reused during an intermediate run, so use the original contact sheets for baseline comparison.
- Headless Chromium verified camera-denied recovery and browser tests verified QR decoding/admission/retry behavior. A physical phone camera and live event network were not exercised. Screen-reader usability still benefits from a human assistive-technology session.
