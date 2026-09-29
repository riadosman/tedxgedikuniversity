# Event-day runbook

Organizer must name supervisor/deputy, technology lead, venue/safety contact, escalation channel, actual doors time and desk/device roster in the application. These unconfirmed facts are not invented here.

## Before opening

- Technology lead verifies real HTTPS health, protected database/storage/job/email checks, monitor alert receipt, latest encrypted off-host backup and restore evidence.
- Supervisor confirms capacity/admission policy and separate doors time; freeze unapproved changes. Export the controlled minimum roster with a reason, number copies and secure custody.
- Staff individually log in/MFA and verify roles. Label devices, assign desks, test Wi-Fi/cellular alternative, chargers/spares.
- Test a clearly identified rehearsal ticket on staging: QR, duplicate rejection, lookup and incident. Do not add fake attendees to production counts. Any production smoke check needs an approved reconciliation method.
- Production/program leads confirm published schedule, responsible people, urgent tasks, runbook and venue emergency procedures. Critical unresolved failures stop opening.

## Opening

Organizer checks the gate and changes closed → online with recent MFA/reason. Admission remains time-gated. Confirm every desk sees the right event and fresh counts; admit only on a new server admission. Registration opening/allocation is a separate policy, not a way to bypass entrance problems.

## During the event

Supervisor reconciles physical flow with permanent admission totals and rejected scans. Unknown results require same-request retry. Program lead follows current/next sessions and publishes reviewed changes. Department leaders update readiness/tasks. Incident owners record severity, assignment, mitigation and resolution. Target announcements appropriately. Dashboard partial updates can be paused and do not replace focused controls.

## Emergencies

| Failure | Immediate action | Recovery authority |
|---|---|---|
| Network/server failure | Stop uncertain admissions; one coordinated paper ledger, numbered roster and actual times | Supervisor coordinates; organizer reconciles |
| Camera/scanner failure | Tested spare/USB scanner or authorized manual lookup | Event Admin/Organizer for manual admission |
| Database issue | Stop writes, alert technology lead, preserve ledger/request IDs | Recovery lead verifies new database before cutover |
| Email failure | Queue/retry and private recovery/manual lookup; message receipt is not admission proof | Technology lead/organizer |
| Lost ticket | Fresh private link or supervised lookup under approved identity policy | Registration supervisor |
| Duplicate ticket | Do not admit again; compare history and actual entry | Entrance supervisor |
| Unauthorized access/lost device | Revoke role/account, secure device, record incident and inspect audit | Organizer/technology lead |
| Safety/power emergency | Follow venue safety plan and emergency contacts; prioritize people | Venue safety lead |

No verified offline scanner mode exists. Manual admission still cannot force an invalid ticket through the application. Paper fallback is one controlled real-world exception process, not independent operation on stale devices.

## Recovery and closing

After outage: manual → reconciling, preview/import ledger, resolve unknown/revoked tickets, compare physical counts, brief desks, then resume online. For server/data loss follow [disaster recovery](../operations/disaster-recovery.md).

At closing: close admission/intake as approved; record final counts and discrepancies. Review incident ownership. Back up reconciled data/files and verify off-host copy. Export authorized reports with purpose/audit. Revoke temporary roles; secure/dispose of roster copies under policy. Review failed mail, unresolved financial/provider items and media permissions. Prepare post-event report, confirm retention holds and schedule approved disposal.
