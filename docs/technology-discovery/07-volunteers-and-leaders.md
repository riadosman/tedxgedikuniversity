# 07 — Volunteer and department-leader specification

Status: proposed delivery option for FR-14–19. Sources: S07 administrative checklist, S11 Turkish administrative pages 1–3 and S09 §§2,5–6. The actual volunteer count, accepted people and assigned leaders are not confirmed. Public recruitment is optional, not a reason to delay registration/check-in.

## Organizational baseline to approve

| Proposed department | Source-proposed lead | Operational scope |
|---|---|---|
| Program and speakers | Tuka Al-Fallah / تقى الفلاح | Curation, editing, sources, rehearsal, speaker support |
| Production and venue | Atika / عاتكة | Room, technical checks, safety coordination, recording |
| Audience and hospitality | Mahmoud Tabaq / محمود طبق | Registration, invitations, arrival, ushers, volunteer coordination |
| Administration / finance | Fifth manager unnamed | Scope must be assigned; do not provision a fictitious account |

Organizer oversees event approval and licence obligations. Technology Lead is an operational capability, not a newly assumed organizational department. Stage manager and presenter are functions still needing named holders. Deputies and contact routes must be confirmed; spellings above are source renderings, not verified identity data.

## Minimal application and roster data

Public application, only if enabled: name, email, relevant skills, availability, preferred department, notice version, optional necessary contact preference. No photo, CV, government ID, birth date, health diagnosis or public social links by default. Do not collect unnecessary emergency/medical details through free text.

Private roster: accepted status, supervisor, department memberships, role, assigned shift start/end, location, acknowledgment, briefing/training status, attendance and an operational contact route. Keep reviewer notes separate from volunteer-visible instructions. Notes must be factual and task-related; prohibit sensitive personal assessments unrelated to the role.

## Workflow and permissions

1. Applicant submits once per event/email; email access verification/recovery follows approved identity policy. Application does not create any staff role.
2. Reviewer records recommendation in assigned department. Event Admin accepts, rejects or waitlists with reason; organizer confirms leaders separately.
3. Acceptance creates roster entry. Create a staff account only if needed for assignments or entry operations; paper-briefed helpers need not all have accounts.
4. Event Admin assigns departments/supervisor. Leader proposes own shifts and tasks for accepted members only. Multi-department volunteers retain separate scoped memberships.
5. Volunteer receives clear instructions, acknowledges shift and records availability changes. Leader records briefing and absence/replacement. Training does not automatically grant scanner access; organizer grants the separate role after readiness check.
6. Withdrawal/reassignment suspends old access and reallocates critical tasks. No active duty is silently orphaned. A leader cannot approve their own promotion, export another department or assign someone outside their scope.
7. Volunteer arrival is logged independently of public attendee check-in. Q03 determines whether a volunteer also attending talks needs an audience allocation; do not silently exempt or double-count them.

## Shift rules

- Proposed shift ranges must fit approved room access or explicitly approved external duties. Public audience hours do not define team shifts.
- Reject end <= start and overlapping active shifts for the same volunteer. Supervisor must explicitly resolve an overlap by changing assignment, not bypass validation without record.
- At least one trained assigned operator and one named backup for each critical station. Exact headcount and stations come from Q09/Q10, not assumed here.
- Critical roles: door operator, exception-desk supervisor, stage cue owner, technical operator, speaker liaison and venue contact. One human cannot perform simultaneous incompatible duties merely because multiple roles are permitted in RBAC.
- A printed/offline roster shows revision, shift, station and supervisor; private application notes are excluded.

## Leader dashboard acceptance

Show own accepted members, unacknowledged shifts, briefing gaps, absences, overdue tasks, blocked dependencies and own incident escalations. Each count links to the relevant scoped records and displays freshness. No other department's application notes, contacts or totals leak through search, filters or exports. Cross-department dependencies may expose only an approved shared task title/status and escalation contact.

Test a leader changing department IDs in URLs, JSON, CSV export requests and file links. Test a reassigned volunteer's existing session. Test a leader who is also a volunteer elsewhere: they must not inherit leader privileges in that other department (AT-07/AT-13).

## Delivery fallback and cut line

If integrated team module is not ready by 4 October, use an approved restricted shared roster/board with exactly these fields, an access owner and a single current version. Rehearse distribution and printouts. Do not mark the software module implemented; record “operational requirement met externally” with evidence. Defer public recruitment, account self-service, shift swaps, ranking/scoring, certificates and mass messaging. The roster and named coverage are still required before the full rehearsal.
