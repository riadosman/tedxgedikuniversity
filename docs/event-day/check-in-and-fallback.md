# Entrance operation and failure recovery

## Before opening

Use named staff accounts on prepared phones/tablets. Verify HTTPS, camera permission, charging, power banks, venue Wi-Fi and backup connectivity. Rehearse with synthetic tickets on the actual phones and in the actual lighting. A browser emulator is not evidence that the camera works at the venue.

The supervisor approves online mode within the configured admission window. Staff open Entrance check-in, set a recognizable device label and start the camera. A USB scanner can enter the same opaque credential field. The screen gives text as well as color. Green `ADMIT` means a committed first admission, not merely a successful QR decode.

| Result | Staff action |
|---|---|
| `NEW_ADMISSION` | Admit the named ticket holder according to the approved identity procedure |
| `ALREADY_ADMITTED` | Do not admit again; route any dispute/re-entry request to supervisor |
| `WRONG_EVENT`, `INVALID`, `REVOKED`, `CANCELLED`, `EXPIRED` | Do not override; resolve with supervisor |
| `ENTRY_PAUSED`, `OUTSIDE_ENTRY_WINDOW` | Follow the supervisor's operating mode |
| Outcome unknown / timeout | Do not assume failure or success. Retry the same request ID before admission |

The camera suppresses repeated frames while a request is unresolved. A retry retains its request ID in the open page. Closing/reloading the page loses the in-memory request, so the page warns before navigation while a request is unresolved. The server's durable receipt remains available; use supervisor reconciliation if the device is lost. The system does not claim distributed offline scanning.

## Controlled manual fallback

1. Supervisor stops all entrance devices and declares manual mode. If the server is unreachable, announce the freeze physically and prevent other desks from continuing online.
2. Collect and resolve any unknown requests using the online receipt/roster where available and the physical admission record. A current database restore alone cannot tell who entered after its backup.
3. Use one controlled desk and a numbered roster/ledger. Record booking reference, unique ledger row ID, actual admission timestamp with timezone, operator and reason. Do not distribute independent admitting copies.
4. Admit only a previously allocated, eligible ticket that has not been admitted. Unrecognized attendees and ambiguous duplicate names go to the supervisor. Do not create replacement audience places when someone exits.
5. After service returns, switch to `reconciling`. Import reviewed CSV headers `reference,ledger_id,admitted_at,reason`; timestamps use ISO 8601, for example `2026-11-21T13:10:00+03:00`. The timestamp here illustrates format, not an admission record.
6. Preview and commit the ledger. A conflicting/unknown ticket blocks the batch for review. Repeating the same batch cannot create a second admission.
7. Supervisor reconciles counts, unknown outcomes, cancellations and paper sheets, records a reason, then reopens online mode. Securely collect and destroy redundant roster copies according to policy.

## Other failures

- **Camera denied/broken:** allow permission, switch prepared device or use supervisor-authorized manual lookup. Do not share accounts.
- **Email missing:** attendee requests a fresh link; staff can find the booking reference/name. Failed outbox jobs remain visible. Email acceptance is not inbox delivery.
- **QR unavailable:** supervisor verifies the attendee under the approved procedure and uses reasoned manual admission.
- **Server/network down:** controlled manual desk above; no locally fabricated successful scan.
- **Power/device loss:** switch to charged replacement, revoke/deactivate a lost device's account access where necessary, reconcile any unresolved request.
- **Restored database:** remain paused until later admissions, revocations, cancellations and erasures have been reconciled. Never reopen solely because `/health/` is green.

The named supervisor/deputy, actual emergency contacts, venue procedures and physical rehearsal sign-off remain event decisions. Do not invent them from generic guidance.
