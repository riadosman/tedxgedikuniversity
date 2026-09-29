# Public experience and Gmail follow-up — 23 September 2026

## Implemented
- Rebuilt shared visitor page layouts: event, speakers, program, location, FAQ, theme, contact, terms and privacy. Registration and recovery retain existing endpoints.
- Replaced the language select/apply flow with three native-language submit buttons. Preserves destination/query; shared form progress handling now retains named submitter values.
- Opened local event `tedxgedik` in free, review-based registration mode, with capacity and licensed capacity 100. Registration remains subject to email verification and organizer approval; submitting does not guarantee a seat.
- Per explicit owner instruction, retained the privacy notice as an unpublished draft. No draft checkbox or false acknowledgement is recorded (`not-published`). Existing approved notices still require acknowledgement. Volunteer intake retains its existing policy.
- Gmail SMTP/TLS authentication succeeded through the local masked setup window. Secrets are stored only in the existing private environment file. No test email was sent; inbox delivery is not verified.
- Added Windows Waitress serving and existing-outbox worker scripts. No database schema or permission changes. Added one private owner recovery code without resetting password or existing Authenticator enrollment.

## Verification
- 76 functional/browser tests passed after the final shared submitter correction, including a three-language regression with and without JavaScript.
- Dedicated visual walkthrough passed: 300 screens (20 routes × 3 languages × 5 widths), plus error/loading/empty/confirmation states. Zero JavaScript errors.
- Actual local registration inspected in all three languages; privacy draft absent, no horizontal overflow. Actual one-click language changes preserve query and route.
- Ruff passed; configured mypy scope passed (64 files). Broader `mypy .` also examines previously untyped scripts/tests and is not a clean baseline.
- Production configuration check passed before attempted launch. Performance load tests were not rerun; the previously observed p95 threshold failure is not resolved by this UI work.

## Current access and limitations
Local preview: http://127.0.0.1:8000/
Dashboard: http://127.0.0.1:8000/staff/tedxgedik/
Private owner access instructions: `.local/dashboard-access.txt` in the parent project folder. Do not publish that file.

Automatic approval review rejected the attempted public server and SMTP worker launch with only “blocked by policy”. No public deployment or running mail worker is claimed. The unused Cloudflare tunnel was stopped; PUBLIC_BASE_URL was restored to localhost to avoid dead public links. Registration is enabled in the local database, but the real-attendee external launch is not complete. Do not distribute localhost verification links to attendees.

A free Quick Tunnel is temporary, changes address on restart and requires the computer/tunnel to remain running. A durable HTTPS origin must be selected and configured before relying on registration email links. Gmail authentication alone does not establish recipient inbox delivery.

Sources:
- https://support.google.com/accounts/answer/185833
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
