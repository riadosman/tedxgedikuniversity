# Policy draft preparation — 17 September 2026

Prepared Turkish event-specific privacy and participation/volunteer terms in `platform/content/policy-drafts.tr.json`, revision `2026-09-17-draft-1`. Installed them in the previously empty event settings using `prepare_policy_drafts`. Original content/decisions were not overwritten. Publication, approval and intake remain unchanged. The command records an audit entry and increments the optimistic-lock version.

The drafts describe actual application data, optional survey consent, QR validation, role-scoped access, volunteer operations and the configured 90-day anonymization review threshold. They do not promise automatic erasure or imply that checking an acknowledgement supplies consent for unrelated processing. No payment service or media consent is invented.

## Facts still requiring institutional confirmation

The repository does not establish the legal data controller and rights-request address, purpose-specific legal bases, hosting/email/storage recipients or cross-border arrangements. The draft marks these explicitly instead of attributing controller status to the university merely from the event name. The retention schedule for backups, provider copies and exports also requires confirmation. The organizer should consolidate these facts with the responsible university contact before approving/publishing the notice. This is a review draft, not a claim of legal compliance.

## Sources reviewed

- [KVKK notice requirements](https://www.kvkk.gov.tr/Icerik/4132/aydinlatma-yukumlulugunun-yerine-getirilmesinde-uyulacak-usul-ve-esaslar-hakkinda-teblig): disclosure topics and separation from consent.
- [Gedik University notices](https://www.gedik.edu.tr/ogrenciler/aday-ogrenciler/kvkk-aydinlatma-metinleri): process-specific notices; no event-specific controller determination inferred.
- [TEDx program](https://www.ted.com/tedx): independently organized event structure.
- Local implementation: `core/forms.py`, `admissions/services.py`, `core/privacy.py`, `docs/security/controls.md`.

Validation: `tests/test_policy_drafts.py` passed, covering draft installation, no implicit approval/opening, preservation of organizer edits and audit uniqueness. Ruff passed. Actual event fields were read back to verify successful insertion and unchanged approval/publication state. No backend behavior or existing application workflow was changed.
