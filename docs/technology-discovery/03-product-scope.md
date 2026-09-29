# 03 — Product definition and scope

Status: proposal; ADR-01/02 approval needed. Sources: F02–F04, F09, F12–F19 and the organizer's request. No active technology service has been discovered.

## Product outcome

Provide one trustworthy public information surface and a small operational system that answers: who has an allocated place, who has entered, who owns each critical task, which program version is approved, and what needs intervention. Target is one event capped at 100 attendees, with a small proposed leadership group and approximately five weeks remaining. It is not an event marketplace or university-wide ERP.

Success targets are proposed acceptance thresholds in document 10, not historical metrics. First release must not fabricate speakers, sponsors, venue approval, ticket availability, completion percentages or a countdown based on unapproved settings.

## Classification

| Module | Classification | Minimum outcome / reason | Delivery boundary |
|---|---|---|---|
| Public website | Required for MVP | Approved identity, date, audience, location status, About, FAQ, support, privacy | Server-rendered pages; verified facts only |
| Public registration | Required for MVP | Clearly defined seat allocation and confirmation, not a contact form masquerading as tickets | Free custom baseline only if approved; external provider alternative |
| Attendee management | Required for MVP | One authoritative roster and statuses | Search, status changes, controlled import/export |
| Secure QR issuance | Required for MVP | Confirmed attendee receives an unpredictable event-scoped credential | Ticket is issued only after allocation |
| QR check-in | Required before event day | Atomic validation and clear feedback on tested phones | No unattended kiosk; no custom native app |
| Volunteer applications | Recommended but optional | Helpful only if open recruitment is still needed | Minimal form or approved external form; no CV uploads |
| Volunteer roster, shifts and briefing | Required before event day | Each helper knows assignment, supervisor and readiness | Shared roster acceptable; integrated CRUD only if core is stable |
| Departments and leaders | Required before event day | Named scopes and approval boundaries | Small fixed department set; no configurable hierarchy engine |
| Tasks and operational readiness | Required before event day | Owners, dates, blockers and evidence for critical items | One existing shared board may satisfy; minimal app if time permits |
| Speaker management | Required before event day | Track approval, rights and rehearsal; publish only approved profiles | Private document tracker; no speaker portal in first event |
| Public schedule | Required for MVP | Show approved sessions or honest “to be announced” | Publish final version before event; no invented lineup |
| Event-day runbook | Required before event day | Versioned cue sheet with local copy and contacts | App or approved document; paper fallback mandatory |
| Incident management | Required before event day | Owner, severity, escalation, resolution and log | Simple restricted log, not emergency dispatch |
| Admin dashboard | Required for MVP | Counts of allocation/waitlist, delivery failures and required actions | Raw numbers and timestamps; readiness view added pre-event |
| Reports and exports | Required for MVP | Minimal roster, reconciliation and private audit export | CSV; no BI warehouse |
| Authentication / permissions | Required for MVP | Individual staff identities and server-side event scope | Attendees need no persistent account |
| Audit log | Required for MVP | Trace changes, access grants, exports and admissions | Append-only application records; no promise of blockchain immutability |
| Budget/procurement module | Phase 2 | Existing finance sheet can handle this scale | No purchasing/accounting system in first release |
| Ticket payments/refunds | Phase 2 unless paid admission is approved | No evidence paid entry is needed | If required now, reassess scope and prefer approved external checkout |
| Self-service attendee portal | Recommended but optional | Cancellation and ticket retrieval useful | Short-lived emailed action links suffice |
| Automated certificates | Phase 2 | Design concepts exist but issuance rules do not | No certificate QR verification service assumed |
| Multi-event SaaS, marketplace, native apps, social network | Not justified for this event | No evidence of need for one 100-person event | Excluded |
| TED API, ticket gateway or custom livestream service | Not justified for this event | No documented integration contract | Manual official tools; link to approved media if applicable |

“Required before event day” is operational necessity, not a commitment to build every listed module. Document 11 identifies which may stay external. If the organizer insists on a single integrated platform for all modules, estimate staffing and reapprove the roadmap before committing.

## Core journeys

1. Public visitor reads approved information → submits minimal request → verifies email → allocation policy produces pending/waitlisted/confirmed status → confirmed attendee receives ticket.
2. Authorized staff scan → server commits admission or returns rejection → staff receive an explicit result. A timeout never becomes an assumed success.
3. Lead views own assignments → removes blocker or escalates → organizer approves critical changes → all users receive the current runbook version.
4. Program team reviews talk and rights → organizer approves public version → publisher releases it without exposing internal documents.

## Dependencies and exclusions

Launch gates: canonical brand, approved public facts, admission/capacity policy, named controller and privacy notice, funded hosting/email, staff account ownership, and an approved operational owner. See Q01–Q09.

No seat map, dynamic pricing, multiple ticket bundles, ticket resale, transfers, facial recognition, government ID collection, automated speaker selection, medical incident records, guest Wi-Fi provisioning, payroll or camera/broadcast control. No real attendee data in development. A form collecting interest may launch separately only with an approved notice and explicit wording that it does not allocate a seat.
