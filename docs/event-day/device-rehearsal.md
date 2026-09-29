# Physical device rehearsal

**Tested:** Chromium on this Windows workstation, mobile viewport, real PostgreSQL/HTTP workflows, generated QR image decoding with the shipped jsQR library, response loss after commit, and automated accessibility/layout checks. Exact final results belong in the rehearsal report.

**Not tested:** physical Android, iPhone, tablet cameras, iOS Safari, actual venue lighting/Wi-Fi/mobile data, damaged screens, battery endurance and screen-reader operation. Desktop emulation does not establish these capabilities.

**Recommended hardware profile:** use supported, security-updated devices already available to the team, rear autofocus camera, tested browser, charger/power bank, readable screen and a tested spare. A laptop with USB QR scanner can provide a staffed fallback. This is a requirements profile, not a purchase recommendation or claim that a particular model works.

For each actual Android/Chrome, iPhone/Safari, tablet/browser and laptop/browser combination, record model, OS/browser version, tester/date, network, results and incident references:

- Login/MFA, idle expiry, reauthentication and logout.
- Camera allow/deny/revoke over the real HTTPS domain, rear camera selection, rotation, stop/restart.
- Printed and screen QR; low brightness, damage, glare, distance and poor lighting. Partial decoding never authorizes admission.
- Valid, modified, wrong-event, expired, cancelled and duplicate tickets. Two devices scan one valid ticket simultaneously: exactly one new admission.
- Wi-Fi/mobile data/slow network; failure before send and after commit. Confirm unknown result, same-request retry and supervisor reconciliation after refresh.
- Scanner failure → spare/USB/manual lookup under the appropriate role; no unauthorized override.
- Keyboard-only controls, visible focus, 200% text zoom, screen-reader results, RTL forms/navigation/tables, and sunlight readability.
- Full doors-open operating duration, charging/overheating, low battery, power failure and device handoff.

Record decoding and server/network latency separately; proposed entrance target is p95 below one second under the agreed network. False green admission, double admission, missing audit actor or unreconciled physical counts is FAIL and stops opening. Camera failure is acceptable only when a tested supervised fallback handles the expected queue. Entrance supervisor signs the matrix; that sign-off is outstanding.
