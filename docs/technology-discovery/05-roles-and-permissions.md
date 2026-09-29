# 05 — Roles, permissions and authorization

Status: proposed, ADR-04. A job title is not a permission grant. Riad's organizer identity is supported by S01–S04; other appointments in S07 remain proposals. There is one event, but every business object and grant is explicitly event-scoped.

## Role necessity and assignment

Organizer, Event Admin, Check-in Staff, Speaker Manager and Content Editor are sufficient business roles. A person may hold several. Technology Lead is a separate operations permission bundle. Department Leader and Volunteer are enabled only if integrated team workflows are delivered. Finance is conditional on a paid-ticket integration. No universal SaaS “Super Admin” is justified. The backup organizer must be a named individual approved by the licence holder.

| Role | View | Create | Edit | Delete / archive | Approve | Export |
|---|---|---|---|---|---|---|
| Organizer | All event business records except authentication secrets; sensitive records only for assigned purpose | Event settings, grants, departments, operational records | Policy, permitted business data, approvals | Archive business records; authorize retention, never erase admission/audit history through CRUD | Roles, policy, public content, final talks/runbook, fallback, conditional refunds | Purpose-limited event data/audit; restricted consent/finance exports require explicit purpose |
| Event Admin | Roster, ticket status, delivery, team and operational data; no private talk evidence by default | Imports, registrations, team assignments, tasks, notices, incidents | Attendee corrections, cancellations, shifts, operational state | Withdraw/cancel/archive; no hard deletion | Volunteer acceptance, operational notices, permitted manual-mode activation | Minimal attendee roster and operational extracts; no bulk private evidence or full financial export |
| Technology Lead | Redacted logs, job/health metadata, deployment/backup inventory | Deployment and recovery records | Runtime configuration through approved infrastructure process | Expire operational artifacts per policy; no business-row deletion | Technical readiness only | Redacted diagnostics; encrypted backups only for recovery, not general browsing |
| Department Leader | Own department roster, tasks/shifts and shared runbook; assigned review applications | Own tasks, shifts, scoped incidents and draft cues | Own assignments/tasks; cannot appoint leaders or move members between departments | Archive own drafts with no active dependants | Task completion and briefing readiness; recommends volunteer acceptance | Own minimum roster/shifts/tasks only if separately granted export permission |
| Volunteer | Own assignments/profile, briefing, designated runbook subset | Own issue reports; own application if recruitment open | Own contact/availability, acknowledgments and assigned task updates | Withdraw own application; cannot delete team records | Own acknowledgment only | Own assignment sheet, no bulk exports |
| Check-in Staff | Minimum ticket/attendee identity and admission state in assigned event | Check-in request, exception report; approved movement records | No direct attendee/ticket/status edits | None | Admission through validation transaction, not policy override | None |
| Speaker Manager | Speaker contacts, talk versions, review/rights/rehearsal records | Speakers, talks, reviews, private documents, program drafts | Preparation and technical requirements | Archive unselected drafts with reference checks; approved evidence by retention only | Review recommendations and preparation checks; not final publication | Speaker preparation pack with approved columns; releases only with explicit restricted export grant |
| Content Editor | Published content, own drafts and public-ready speaker fields | Content revisions and candidate public assets | Draft pages/FAQ/schedule copy | Unpublished unreferenced drafts only | None | Public content preview, not private roster |
| Finance / Ticket Admin (conditional) | Order totals, provider references, necessary payer contact | Refund request/reconciliation record | Reconciliation notes; never directly mark paid | None; statutory record retention controlled separately | No self-approved refund; organizer approval required | Financial report only; no full attendee/speaker documents |

## Resource matrix

Codes: `R` read; `C` create; `U` update; `A` approve; `X` export; `S` archive/soft-delete; `—` denied. `(dept)` own approved department; `(own)` own records; `(min)` field-limited; `(grant)` separate explicit elevated grant. No entry grants hard delete. Public visitors read published fields only and invoke their own purpose-bound attendee actions.

| Resource / action | Organizer | Event Admin | Tech | Leader | Volunteer | Check-in | Speaker Mgr | Editor | Finance |
|---|---|---|---|---|---|---|---|---|---|
| Event/capacity policy | RCUA | R; pause only | — | R(min) | R(min) | R(min) | R(min) | R(min) | R(min) |
| Role grants / leader appointments | RCUAS | R(min) | — | R(own) | R(own) | R(own) | R(own) | R(own) | R(own) |
| Public content revisions | RCUAS | R | — | R | R | R | RCU(min) | RCUS(draft) | R |
| Public publication | A | — | — | — | — | — | — | — | — |
| Attendee personal records | RCUXS | RCUXS | — | — | — | R(min) | — | — | R(min, conditional) |
| Ticket cancel / rotate | RCUA | RCU | — | — | — | R(min) | — | — | R(min) |
| Admissions transaction | RC | RC | — | — | — | RC | — | — | — |
| Manual-mode change | A | A(delegated) | R | R(min) | — | R | — | — | — |
| Volunteer applications | RCUAS | RCUAS | — | RU(dept,review) | RCU(own) | — | — | — | — |
| Memberships / departments | RCUAS | RCU(members) | — | R(dept) | R(own) | — | — | — | — |
| Shifts / briefing | RCUXS | RCUXS | — | RCUS(dept),X(grant) | RU(own) | R(own) | R(min) | — | — |
| Tasks | RCUXS | RCUXS | R(assigned) | RCUS(dept),X(grant) | RU(assigned) | R(assigned) | RCU(assigned) | RCU(assigned) | RCU(assigned) |
| Runbook | RCUAX | RCUX | R(technical) | RCU(dept draft) | R(min) | R(min) | RCU(draft) | R(public) | — |
| Incident records | RCUAX | RCUX | RCU(technical) | RCU(dept) | C,R(own) | C,R(own) | C,R(own) | C,R(own) | C,R(own) |
| Internal announcements | RCUAS | RCUAS | R | R(dept) | R(own) | R(own) | R | R | R |
| Speaker evidence | RCUA,X(grant) | — | — | R(min,production grant) | — | — | RCUS,X(grant) | R(public-ready) | — |
| Private files | R(scope),X(grant) | R(ops scope) | — | R(dept) | R(assigned) | — | RCU(speaker) | RCU(public drafts) | R(finance) |
| Audit | RX | R(ops subset) | R(redacted) | R(own task history) | R(own actions) | R(own receipt) | R(speaker history) | R(content history) | R(finance history) |
| Payments / refunds | RA,X(grant) | R(status only) | R(redacted health) | — | — | R(validity only) | — | — | RCU(request),X |
| Privacy requests / retention | RCUA(grant) | R(status only) | Execute approved job | — | Own request only | — | — | — | Retention hold reference only |
| Infrastructure / backups | R(health) | R(health) | RCU(recovery) | — | — | R(health) | — | — | — |

## Enforcement rules

1. Resolve session → active user → active event grants → department/ownership scope → allowed action → field allowlist. Recheck all of these in the service handling the mutation. A hidden UI button is not authorization.
2. Use composite event/object foreign keys and event-filtered queries. Never trust an `event_id`, `department_id`, owner ID, role string or file scope provided by the browser.
3. For multiple grants, evaluate each permission within its own scope. A leader in Production plus volunteer in Registration must not gain Registration leadership through a union of departments.
4. Ticket management links and QR credentials are different capabilities. QR possession can be presented for admission only; it never grants profile edits, cancellation, account creation or export.
5. Private downloads use fresh authorization and short expiry. Prevent public cache storage of staff pages, tickets and exports. Object IDs being UUIDs do not replace authorization.
6. Every approval targets a specific revision. If one person holds editor and organizer roles, self-approval is allowed only as the organizer, with a visible audit record; a second reviewer is recommended for sensitive releases, not invented as an existing staffing requirement.
7. Elevation requires recent MFA, explicit reason, limited scope and expiry. Infrastructure operators inherently can access backups/configuration; document, restrict and log break-glass use. App RBAC cannot prevent a database superuser from accessing data.
8. Critical business records are cancelled/archived, not hard-deleted. Retention erasure is a separate approved workflow with holds, anonymization and backup-expiry handling.
9. Test list views, direct IDs, CSV, private file URLs, background jobs, stale sessions and alternative HTTP methods. Request-level and object-level denial are both required (AT-07).

This design follows the deny-by-default and per-request verification principles in [OWASP Authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). The exact matrix is a project proposal, not supplied by a framework.
