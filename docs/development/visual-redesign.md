# TEDxGedik visual system and redesign

Updated: 17 September 2026.

## Scope and implementation

The existing Django application, PostgreSQL data, permissions and business workflows remain in place. Changes are presentation templates, CSS, browser interactions, presentation-only template filters and regression tests. No migrations, account resets, new event facts or payment changes.

- `platform/static/design-tokens.css` defines the shared palette, typography, spacing, radius and motion variables. System Arial/Helvetica avoids third-party font requests. Responsive breakpoints are 700px and 1100px, with a 1600px wide-screen adjustment.
- `platform/static/app.css` implements the public editorial layout and operations workspace. Red actions, ink navigation, neutral surfaces and thin rules replace decorative crosses and repeated rounded cards. Success, warning and error labels remain readable without color.
- `templates/components/form-fields.html` shares labels, help text, field errors and checkbox layout across public, staff and authentication forms. Existing field widgets, validation, CSRF and submitted actions are preserved.
- Public homepage now leads with the stored event identity, localized date, participation links and source-backed introduction. Speakers remain unpublished until approved. No unconfirmed venue is promoted as confirmed.
- Public navigation has a keyboard-operable mobile menu, Escape-to-close with focus return, and click-outside dismissal. The footer uses the white event logo. Registration remains accessible from the hero and navigation.
- Speaker cards/detail, program timeline, public information/CMS pages, registration/volunteer/recovery forms, confirmations, private ticket and account security screens share the visual system. Program times are formatted from approved snapshots, not draft schedule fields.
- Staff dashboard, permission-filtered sidebar, all resource lists/details/forms, accounts, reports, department panels, tasks, incidents, speakers, CMS and scanner inherit consistent controls. Mobile resource tables render labelled rows; contained table scrolling remains available for other report formats.
- Actual database statistics and existing role scopes are unchanged. Critical/high incident rows receive emphasis. No fabricated readiness percentage or team count was added.
- Ticket branding and QR padding preserve scannability. Check-in uses its existing authoritative outcomes and retry mechanism, with stronger result panels. No client-side admission decision was introduced.
- Cancelling a destructive-action confirmation no longer disables the form's submit button.

## Assets

Unmodified repository logos: `tedx_logo/logo-black.png` and `tedx_logo/logo-white.png`, served through the existing `platform/static/brand/` copies. No generated replacement identity, external fonts or stock imagery.

Poster concepts were inspected but excluded: they print a venue that the source map still classifies as unconfirmed. Actual approved speaker portraits, when present in the database, continue to use the authorized public-image endpoint. Empty speaker states remain honest.

## Verification

Baseline: 61 tests passed before edits. Final full suite: 62 tests passed (one existing Django deprecation warning). Ruff formatting/lint, mypy across its configured 62 source files, and translation checks passed. EN/TR/AR catalogs each contain 623 server messages and 33 JavaScript messages with no untranslated active entries. Full output is recorded in `.local/design-final-tests.txt`.

`tests/test_design_browser.py` exercises 320, 375, 390, 430, 768, 1024, 1440 and 1920px browser viewports. It checks public home, open registration and volunteer forms, populated speaker detail, published program, confirmed digital ticket, staff dashboard, scanner, populated ticket list, speaker detail and incident creation form. Every staff resource list is checked at 390px. Turkish LTR and Arabic RTL routes are checked at 390px. Tests use isolated synthetic PostgreSQL records, never the actual event database.

Automated axe rules are checked on the representative routes at 320px and 1440px. Keyboard menu closing, cancelled ticket confirmation and unchanged ticket state are verified. Existing browser tests cover real registration/approval, QR decoding and response-loss retries. Physical phones, cameras and screen-reader users were not tested in this redesign.

The local preview also passed 30 English/Turkish public route and automated accessibility checks. Screenshot artifacts are under `.local/test-artifacts/design/`, with public preview images under `.local/test-artifacts/`. Automated checks do not establish complete WCAG compliance.

## Content and remaining limits

Final speakers/photos, theme approval, venue and registration opening remain organizer-controlled. The public preview intentionally shows the preparation notice and closed applications. Event-specific untranslated CMS content still needs an approved translation; interface catalogs remain maintained separately.

No real-device compatibility or production readiness claim is made. Existing external deployment/readiness blockers are unaffected. Native browser confirmation dialogs remain in use for destructive actions; there is no unnecessary custom modal framework. No live payment or ticket purchase flow was invented.

Preview: http://127.0.0.1:8010/ (Turkish: `/?lang=tr`).
## Settings and speaker-photo usability follow-up

The event settings form now groups all existing fields into six labelled fieldsets, provides section navigation, explains registration/publication/volunteer gates and uses local date-time inputs with the event timezone displayed. Underlying validation, recent MFA, version checks and audit remain unchanged.

Fixed form localization: rendering individual fields through the shared component bypassed the old full-form renderer's label translation. Labels now translate before rendering while preserving organizer-defined custom questions. The translation extractor now includes Event model choices, fixing missing Free/Paid/Undecided/First Come and admission-mode labels.

The speaker form explains that Photo selects an already uploaded document and provides a permission-gated new-tab upload link. Save the speaker before leaving, upload PNG/JPEG using Public Candidate scope, then edit the speaker to select the image. Publication still requires the existing clean scan and consent gates. No scan bypass or automatic public upload was introduced.

The responsive browser regression now includes settings and new-speaker screens at all eight widths, axe checks at 320/1440px, Turkish labels/payment choices, six settings sections, date-time widgets, and the upload link. EN/TR/AR catalogs have 653 server and 33 JavaScript messages each, with no untranslated active entries.

### Volunteer opening guidance

Added a five-step settings guide with links that focus the relevant fields, live filled/missing indicators, and explicit save semantics. Notice text, version label and actual human approval are explained separately. No policy text is fabricated and no consent/approval is automatically enabled. Missing privacy prerequisites now produce field-level errors plus a linked error summary. Server-side model gates remain active. Guidance is translated in EN/TR/AR. Regression tests cover missing prerequisites without database mutation and Turkish guide navigation/live indicators.

### Simplified organizer settings

Main settings now show event identity/location, public timing and attendee/application status. Prepared privacy/terms and advanced configuration use collapsible sections. The step guide is optional rather than occupying the top of the screen. Error links and native validation open the affected disclosure before focus. All original fields and approval gates remain available.

The Turkish policy copy was shortened at the organizer's request and saved as draft revision 2026-09-17-draft-2. Original full copy remains in content/policy-drafts-v1.tr.json. The real database was updated only after comparing both existing texts with the previous generated revision and checking that neither was approved. Unknown institutional facts remain identified in one compact review paragraph; no controller identity or approval was fabricated.
