# Interface language maintenance

English, Turkish and Arabic application catalogs are in `platform/locale/<language>/LC_MESSAGES/`. The event's `enabled_languages` controls the selector; it does not approve translated event content. Arabic sets document direction to RTL. Keep public page translations and email templates in their event/language records and obtain content approval before enabling them.

From `platform/`, run `../.venv/Scripts/python.exe scripts/translations.py` after changing application labels. It extracts Python tr/gettext calls, template translate/default_ui literals, resource/form labels and JavaScript gettext calls, updates PO files and compiles MO files without system gettext. Edit PO translations, then run the command with `--check`. The updater preserves returning obsolete translations without duplicate entries. Arabic uses its six-form plural rule. See `platform/locale/coverage.json` for the current extracted inventory.

Mark new literal interface strings explicitly. Dynamic labels need an explicit extraction source; extraction coverage cannot prove every runtime string is localized. Do not translate attendee names, custom registration questions, speaker biographies, policy text or event facts through application gettext. Framework validation uses Django's catalogs. Keep machine status codes stable and translate display labels.

Attendee/volunteer messages persist the selected enabled language. Workers require a matching approved template and expose missing templates as retries/failures. Staff accounts have no separate preferred-mail-language profile; operator-context language is the current fallback. Authentication reset templates use request language. Provider acceptance is distinct from inbox delivery.

Chromium tests exercise English workflows and Turkish/Arabic mobile dashboards, direction, overflow and selected axe checks. Screenshots were visually reviewed. Native-language editorial approval, populated event content, real mobile browsers and assistive technology still need rehearsal. Catalog completeness is not an assertion that every dynamic business-error message or event-specific text has been translated.

The public-website follow-up adds paired English/Turkish CMS drafts and shareable `?lang=tr` links; see [website update](public-website-update.md). Interface catalogs now contain 625 Django and 33 JavaScript messages per language.
