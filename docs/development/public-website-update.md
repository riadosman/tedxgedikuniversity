# Public website and Turkish preview

17 September 2026. The existing public views now support a read-only local preview of an unpublished event. Both `DEBUG` and `LOCAL_EVENT_PREVIEW` must be enabled and `PRODUCTION` must be false. Production publication filtering remains enforced. Unpublished preview submissions are rejected server-side; registration, recruitment, payment and policy approvals are not changed.

The local homepage is `http://127.0.0.1:8010/`. Append `?lang=tr` for Turkish or `?lang=en` for English. The language cookie preserves the selection while following links. The language form removes an old `lang` query parameter from its return URL so it can change a shared-link selection.

Routes under `/e/tedxgedik/`: `about/`, `theme/`, `speakers/`, `program/`, `venue/`, `faq/`, `contact/`, `privacy/`, `terms/`, `register/`, `volunteer/`, `recover/`, `volunteer-recovery/`. Unknown page keys still return 404. The local-only bypass does not make private accounts, attendee records or files public.

## Content and assets

- Original `tedx_logo/logo-black.png` and `logo-white.png` are copied unchanged into the application static assets. The black-text logo is displayed on a light header. Original event files are not edited.
- `platform/content/event-pages.json` contains paired English/Turkish drafts for eleven page topics. The source map and original Turkish introduction/detailed PDFs inform the content. The licensed identity follows correspondence rather than conflicting older PDF wording.
- The homepage displays the existing event record's date, planned program hours and licence audience limit, plus an expanded introduction, theme/program/FAQ links, speaker announcements and volunteer information.
- Proposed theme and talk count remain labelled as proposals. Exact room, entrance opening, price, public contact, privacy and terms remain unconfirmed. No speakers, testimonials, payment integration or final venue facts were invented.
- `python manage.py prepare_public_content --slug tedxgedik` creates missing drafts and expands only exact legacy imported text. It preserves organizer edits and published snapshots. It enables the requested English/Turkish selection but does not publish or open intake. In this workspace, 22 draft page records were prepared.
- Public application pages display translated explanatory content and a closed message, rather than a local-preview 404. Private ticket access still requires a valid credential.

## Validation

61 tests passed on PostgreSQL/Chromium, including production preview denial, read-only unpublished forms, bilingual routes, content-import idempotency and preservation of edits. Ruff and configured mypy checks passed. Separately, 15 real local routes in each language returned 200 and passed the selected axe checks; home/registration/venue mobile layouts did not overflow. English desktop and Turkish mobile screenshots were visually reviewed. This is not a physical-device or full WCAG certification.

Production readiness gates in the existing checklist remain applicable. This update enables a useful local preview, not production registration or paid checkout.
