# TEDxGedik University — technology discovery

> Implementation update, 17 September 2026: the organizer has authorized the full platform. Statements below about a documentation-only phase, an MVP, or tests not yet run describe the discovery baseline. See [current implementation and evidence](../development/implementation-status.md) for the implemented system and remaining gates.

Status: **proposed requirements for organizer review; implementation not authorized by this package**. Discovery date: **17 September 2026**. Authoring language: English, matching the discovery request. Existing Arabic/Turkish event guides remain unchanged.

The intended product is a **TEDx Event Operations Platform** supporting one university event. This workspace is currently an event-document and artwork collection, not an application or Git checkout. There are 34 calendar days until the documented event date. No dependencies, accounts, services, infrastructure, or application features were installed or created during discovery.

## Read in this order

| Document | Purpose |
|---|---|
| [01 — Facts and source map](01-event-facts-and-sources.md) | Repository findings, event facts, source quality, contradictions |
| [02 — Stakeholders](02-stakeholder-requirements.md) | Goals, actions, information, permissions and dependencies |
| [03 — Product scope](03-product-scope.md) | MVP, event-day necessities, optional and deferred capabilities |
| [04 — Functional requirements](04-functional-requirements.md) | Identified workflows with acceptance criteria |
| [05 — Roles and permissions](05-roles-and-permissions.md) | Server-enforced access matrix and approval boundaries |
| [06 — Ticketing and QR](06-ticketing-and-qr.md) | Capacity, credential lifecycle, atomic check-in and fallback |
| [07 — Volunteers and leaders](07-volunteers-and-leaders.md) | Recruitment, assignments, shifts and department scope |
| [08 — Architecture](08-technical-architecture.md) | Alternatives, proposed components and deployment boundaries |
| [09 — Data model](09-data-model.md) | Relational entities, constraints, indexes and lifecycle |
| [10 — Security and non-functional requirements](10-security-privacy-and-nfr.md) | Measurable service targets and data handling |
| [11 — Roadmap](11-mvp-roadmap.md) | Dependencies, deliverables and cut-off decisions |
| [12 — Acceptance and testing](12-acceptance-and-testing.md) | Test scenarios, requirement coverage and release gates |
| [13 — Decisions and questions](13-decisions-and-open-questions.md) | Exact unresolved decisions and approval record |
| [14 — External constraints](14-external-constraints.md) | Current authoritative guidance and verification tasks |
| [Inventory](repository-inventory.md) | Paths and fingerprints of the 41 pre-existing files |

## Interpretation

- **F**: source-supported event fact or documented plan. A plan is not proof of completion.
- **T**: observed existing technical decision or implementation. None establishing an application stack were found.
- **P / ADR**: proposed product or architectural decision; not approved merely because documented.
- **Q**: missing information affecting a specific implementation or launch gate.
- **X**: external constraint; verification status and responsible party are recorded in document 14.
- **C**: contradiction or unresolved mismatch between sources.
- **FR / NFR / AT**: proposed functional requirements, non-functional requirements and acceptance scenarios. “Must” defines the proposed acceptance contract, not an assertion of implemented behavior.

MVP means the first usable release, not everything needed on event day. “Required before event day” can be satisfied by a documented, rehearsed external/manual workflow where expressly allowed; it does not mandate a custom module.

## Discovery report

**Confirmed:** the licence email names TEDxGedik University, 21 October 2026, University / Community, one event, up to 100 attendees. Local plans specify 13:00–16:00 for the audience and 12:00–17:00 for the team. Read-aloud opening permission is preserved in the correspondence. Source details and qualifications are in document 01.

**Proposed:** a modular monolith with a server-rendered public site, PostgreSQL, event-scoped staff permissions, free registration if approved, opaque QR credentials, transactional check-in, and one controlled manual fallback. Django is the provisional architecture recommendation; team skill and hosting approval can change it before implementation. Keep detailed operations in existing shared documents where a custom feature would threaten readiness.

**Missing:** registration/payment policy, approved venue and capacity allocation, languages, role holders, existing off-repository systems, technology staffing, controller/privacy decisions, approved hosting and email, and event-day connectivity/device availability. Document 13 asks only unresolved questions.

**Risks:** short delivery window; inconsistent branding and venue evidence; unverified network/setup access; external data-transfer and payment decisions; overbuilding; and treating a draft or untested scanner as operational. The supplied correspondence contains private contact and meeting-access information and must never become a public site asset.

**Recommended next step:** organizer reviews ADR-01 through ADR-07 and Q01–Q09. After the foundation gate in document 11 is met and implementation is explicitly requested, start **Phase 1 — Foundation** with a private application directory, synthetic fixtures, staff authentication/authorization and database constraints. Do not start paid ticketing, publish provisional facts, or migrate live attendee data before their gates pass.

## Review record

| Baseline | Reviewer | Decision | Date |
|---|---|---|---|
| Discovery v1 | Event Organizer / Technology Lead | Pending | — |

Documentation validation checks structure, traceability and references only. It is not application, security, payment, camera, load or recovery testing.

## Documentation validation — 17 September 2026

Verified 16 Markdown files, local source links, UTF-8 text, table shapes and balanced code fences. All 34 functional requirements contain the required description, role, preconditions, workflows, errors, data, permissions, acceptance, priority and dependency fields. The 22 acceptance scenarios reference all 34 functional requirements; 18 non-functional requirements define proposed measurable targets. SHA-256 comparison confirmed all 41 pre-existing files remained unchanged. Temporary inspection images were removed. No application or production-readiness test was run.
