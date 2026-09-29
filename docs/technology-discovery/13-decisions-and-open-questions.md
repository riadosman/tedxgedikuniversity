# 13 — Decisions, approvals and unresolved questions

> Implementation update, 17 September 2026: the organizer has authorized the full platform. Statements below about a documentation-only phase, an MVP, or tests not yet run describe the discovery baseline. See [current implementation and evidence](../development/implementation-status.md) for the implemented system and remaining gates.

Status: open review log, 17 September 2026. No approval is inferred from silence or from writing this package. Existing source-backed facts are in document 01; no request is made to restate the known date, audience hours or email licence cap.

## Existing decisions versus proposals

| ID | Decision | Evidence / status | Approval authority |
|---|---|---|---|
| ED-01 | Discovery and requirements first; no full application generation | Current organizer request U01 — confirmed instruction | Organizer |
| ED-02 | Existing workspace is document/artwork-only; no established app architecture | Recursive inventory and Git/config inspection — observation, not a chosen stack | Not applicable |
| ED-03 | Preserve correspondence and existing event documents as sources | S16 and discovery request — confirmed constraint | Organizer |
| ADR-01 | Prefer Django/PostgreSQL modular monolith if team skills/host fit; static+external alternative if capacity insufficient | Proposed; document 08; no installed framework | Organizer / Technology Lead |
| ADR-02 | Free registration, one general-admission type and verified first-come allocation with waitlist; external provider preferred if paid or capacity insufficient | Proposed only; free/selection policy unknown | Organizer; finance if paid |
| ADR-03 | Opaque 256-bit QR; single permanent first admission; transactional event/ticket locks; one manual fallback desk | Proposed; documents 06/09 and F03/C08 | Technology Lead and entry supervisor; organizer policy approval |
| ADR-04 | Invite-only individual staff accounts; scoped roles; elevated MFA; attendees use purpose-bound links | Proposed; documents 05/08 | Organizer / Technology Lead |
| ADR-05 | Narrow MVP; operational roster/tasks/speaker evidence can remain in approved shared tools | Proposed; documents 03/07/11 | Organizer and affected leads |
| ADR-06 | Private hosting/storage/email with no tracking; proposed retention and recovery targets | Proposed; document 10. Vendor, geography and lawful handling unapproved | Controller/privacy contact; organizer; Technology Lead |
| ADR-07 | Use licensed email name provisionally; reconcile all branding/venue/theme/schedule conflicts before publication | Proposed resolution process for C01–C10, not implicit approval of artwork | Organizer; venue/program contacts |

Architecture decisions describe alternatives, consequences and gates in linked documents. Mark each accepted/rejected/superseded with reviewer/date and reason; amend dependent requirements before implementation.

## Only unresolved material questions

| ID | Question | Why unresolved / source | Blocks | Proposed decision owner / target |
|---|---|---|---|---|
| Q01 | Is attendance free or paid, and is allocation open first-come, invitation-only or application-reviewed? Are any places reserved, and when should registration open/close? | S09 §1 lists policy as unconfirmed; poster indicates registration only | Public CTA, registration state machine, pricing and provider branch | Organizer by 20 Sep |
| Q02 | Is Kartal Konferans Salonu the approved room? What are its exact address/building, booking evidence, venue contact, access times and permitted public arrival time? | C02/C04: poster vs unconfirmed room; audience/team hours already documented | Venue page, runbook and technical rehearsal | Organizer + university/venue before venue publication |
| Q03 | Which categories count toward the licensed audience and venue occupancy, what attendee allocation remains after approved reservations, and what is the re-entry/cancellation cutoff policy? | 100 cap known; staff/speaker/volunteer accounting and lifetime audience implementation not settled | Capacity model and admission exceptions | Organizer/licence contact + venue before registration |
| Q04 | Are the named proposed leads accepted, who is fifth manager/finance lead, and who are backup organizer, stage manager, public publisher and entry supervisor? | S07/S09 explicitly proposed; no confirmed account roster | Role provisioning, approvals and event staffing | Organizer by foundation gate |
| Q05 | Which languages are required for the public site, staff scanner and talks? Which theme/tagline and logo variant are approved? | C01/C03; Turkish/Arabic documents do not decide runtime languages | Content model, translations and asset publication | Organizer/program lead before public release |
| Q06 | Are there off-repository websites, domains, source repos, registration lists, email accounts or university-approved tools already in use, and who owns them? | No implementation/config found locally; does not prove external absence | Avoid replacement/duplication; migration/architecture | Technology Lead by 20 Sep; references/access route only, no secrets in replies |
| Q07 | Who will implement/support the platform, with which familiar stack and time availability? What funded hosting/storage/email/backup options and domain/DNS ownership are available? | No technical staffing or approved service budget in sources | ADR-01, authentication/email setup, delivery commitment | Organizer / Technology Lead by 20 Sep |
| Q08 | Who is the data controller/privacy contact, and what processing grounds, notices, filming/minor rules, recipient transfers, retention/holds and hosting regions are approved for this event? | No event-specific notice, policy or controller designation found | Personal-data collection, cloud providers, survey/media transfers | Organizer + appropriate university/privacy reviewer before live data |
| Q09 | Which actual phones, trained operators, backup operators, Wi-Fi/cellular links, power and rehearsal access will be available at the entrance? | S05 lists checks, no test results; 12:00 setup window is short | Scanner technology and go/no-go | Production/registration leads by 4 Oct; rehearsal by 18 Oct |
| Q10 | Is volunteer recruitment still needed; how many helpers/stations/shifts are required, and will shared roster management suffice? | No count or accepted roster found | Optional application module and integrated team scope | Organizer/registration lead by 4 Oct |
| Q11 | Where are the final speaker list, approved talk/public-profile revisions, signed releases and current official event-page/organizer-resource references? Does the team already have these outside the workspace? | S05 workflows and deadlines exist, not completed records; licence portal not inspected | Profile publication, program readiness and post-event handoff | Program lead / organizer; selection target 20 Sep, schedule 11 Oct |
| Q12 | If paid: which legal merchant, approved provider/currency, price, fees, settlement schedule, refund/dispute policy and invoicing responsibilities apply? | No paid policy/provider contract found | Any money collection or paid schema implementation | Organizer/finance/privacy reviewer before enabling paid branch |
| Q13 | Does the no-outside-sponsorship commitment in the application still govern, or has TED approved a clarified arrangement? | C06; generic sponsorship guidance does not resolve a particular commitment | Sponsor content and related financial agreements | Organizer/licence contact before sponsor promises/pages |
| Q14 | Which non-core modules must be integrated now rather than satisfied by approved shared documents, and who maintains the system after closeout? | U01 lists possibilities, S09 recommends lightweight tools | Final MVP staffing and long-term handover | Organizer before committing Phase 5–7 development |

Suggested first review bundle: Q01, Q04, Q06–Q08 and ADR-01–06. These determine the foundation and registration branch. Venue/language/branding decisions can proceed in parallel before public release; final speaker content is not a reason to invent placeholder identities.

## Risk register

| Risk | Likelihood / impact (qualitative proposal) | Mitigation / owner | Trigger to escalate |
|---|---|---|---|
| Scope exceeds 34-day window | High / high | Strict core-first gates; organizer approves cuts | Core not tested by 11 Oct |
| Single technical operator | Unknown / high | Name deputy and rehearse restore/deploy | No deputy by readiness rehearsal |
| Venue/device/network unverified | Unknown / high | Actual-site camera/network test and manual desk | No reliable online path or safe fallback |
| Branding/room/sponsor contradictions | Observed / high | C-register, approval before publishing | Conflicting material requested for release |
| Privacy/controller/transfer unresolved | Observed missing evidence / high | Q08/X07/X08 review; synthetic data only | Launch requested without approved notice/handling |
| Paid vendor delay | Conditional / high | Hosted provider evaluation and paid gate | Merchant/refund/webhook contract missing |
| Duplicate or excess admissions | Medium without controls / high | Transaction constraints and race tests | Any AT-03/04/06 failure |
| Email non-delivery | Unknown / medium | Sender verification, outbox, bounce handling, desk recovery | Oldest confirmation >5 min or high failure rate |
| Stale manual roster/restore | Medium / high | Freeze writes, single ledger, supervised reconciliation | Unaccounted physical entry |
| Publishing private repository sources | Medium / high | Private repo, explicit public-asset allowlist, secret scan | Build copies root directory or indexes correspondence |

## Approval/change record template

| Record | Proposed value | Accepted value / reason | Reviewer | Date | Affected FR/NFR/AT | Evidence link |
|---|---|---|---|---|---|---|
| ADR/Q/C ID | — | Pending | — | — | — | — |

Record changes to admission policy, cap, provider, identity, controller, event times and public content versions. A mockup, email “sent” flag or checked checklist is not a substitute for the corresponding evidence. No real credentials should be pasted into this log.
