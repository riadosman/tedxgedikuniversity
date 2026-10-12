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

## Confirmed event logistics

Source: TED event manager details provided and confirmed by the organizer on 4 October 2026.

- Date: 21 November 2026.
- Program: 13:00–16:00, Istanbul time (UTC+03:00).
- Check-in: 12:45–13:00, approved by the organizer.
- Venue: Kartal conference, Istanbul, İstanbul, Türkiye.
- Licence type: University.
- Licence term: 17 August 2026 02:00 +03 to 17 August 2027 02:00 +03.

## Confirmed theme and registration

Theme: **From Ideas to Impact**

Bridging Theoretical Knowledge with Real-World Practice

Knowledge often remains confined to classrooms, books, and theories, while its true value emerges when it is translated into practice, experience, solutions, and meaningful impact.

This theme explores a fundamental question: How do we move from knowing to doing?

We seek to explore the connection between theoretical concepts and practical applications, and how the knowledge we acquire can move beyond traditional learning to become a tool for understanding the world, addressing its challenges, and creating new solutions.

It is not about choosing practice over theory. Rather, it is about discovering the space where ideas meet action, knowledge meets experience, and learning creates impact.

Open to the public. Seats are available as confirmed by the organizer on 4 October 2026. Register or apply: https://tedxgedik.vercel.app/

Canonical event details: `platform/content/confirmed-event.json`.

## Confirmed program and stream descriptions

Approved by the organizer on 4 October 2026 for 21 November 2026. All times are Istanbul time. This six-section program supersedes earlier schedule alternatives. Two talk sessions contain four 15-minute talks each, plus ten minutes of transitions per session. Speaker names and talk order remain pending.

### 1. Check-in and Welcome | 12:45–13:00

Welcome to TEDxGedik University. As our audience arrives and takes their seats, get ready for an afternoon of ideas, discovery, and new perspectives. The opening begins at 13:00, Istanbul time.

### 2. Opening and Introduction | 13:00–13:10

We open TEDxGedik University with a welcome to our audience and an introduction to TEDx and the purpose of our gathering.

### 3. Talk Session 1 | 13:10–14:20

Our first session brings four speakers to the stage to share ideas and perspectives from different fields. Join us for talks that encourage curiosity, reflection, and conversation.

### 4. Intermission | 14:20–14:40

We’re taking a short break. Reflect on the ideas from our first session, share your thoughts, and join us again at 14:40, Istanbul time, for the next four talks.

### 5. Talk Session 2 | 14:40–15:50

Our program continues with four more speakers, bringing new questions, experiences, and ideas to the TEDxGedik University stage.

### 6. Closing and Thank You | 15:50–16:00

Join us as we close TEDxGedik University and thank the speakers, volunteers, organizing team, and audience who made this gathering possible. We’ll also explain how to share your feedback through the audience survey.
