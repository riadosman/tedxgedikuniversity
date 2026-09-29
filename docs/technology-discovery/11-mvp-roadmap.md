# 11 — Phased roadmap and delivery gates

Status: proposal as of 17 September 2026; **no implementation started**. The event date leaves 34 calendar days. Staffing, availability, budget and current off-repository progress are unknown, so these are target windows and scope gates, not an estimate guaranteeing completion.

## Delivery order

Critical path: decisions → foundation → approved public content → registration/allocation/delivery → scanner → full operational rehearsal. Speaker preparation and volunteer/operations planning begin immediately in existing documents; their later phase numbers do not imply waiting until software is ready. Do not move the established speaker-review deadline to accommodate new software.

| Phase / target | Scope and dependencies | Deliverables | Acceptance gate | Main risk | Explicitly out of scope |
|---|---|---|---|---|---|
| 0 — Discovery and decisions, 17–20 Sep | This package; Q01–Q09, ADR-01–07; confirm off-repository systems and staffing | Reviewed baseline, controller/hosting decision route, canonical content and ownership table | Organizer records decisions; no assumptions silently approved | Unresolved admission policy or engineering capacity | Application code, installations, purchases, account creation |
| 1 — Foundation, target 20–23 Sep | Approved architecture, maintainers, hosting approach and role model | Private app directory/repository plan, locked stack, staging with synthetic data, auth, scoped services, DB constraints, audit/outbox and CI | FR-12/13/28, AT-07/09/17 pass; deploy/rollback smoke | Authentication/hosting discovery expands | Real attendees, payments, complex volunteer portal |
| 2 — Public website/content, target 22–26 Sep | Phase 1; approved identity/date/language/contact, publication rules | Accessible public pages, revisions and approvals, safe assets | FR-01/02/24; AT-01/12; no provisional room/lineup represented as final | Artwork/venue conflict; content delay | Fake speaker cards, homepage sponsors, autoplay media, custom CMS platform |
| 3 — Registration/ticketing, target 24 Sep–2 Oct | Admission/controller/notice/email/capacity approval; Phase 1 | Verified intake, allocation/waitlist, tickets/QR, email queue, cancellation, roster import/export | AT-02/03/05/06/08/11/15; tested backup; source of truth recorded | Deliverability, privacy or merchant delays | Paid checkout unless separate gate; seat maps, bundles, transfers |
| 4 — QR check-in, target 1–7 Oct | Valid allocation, staff roles, real-device/network access | Transactional scanner, request receipts, search, manual-mode controls and ledger | AT-04/09/10/14; signed mobile prototype result | Venue Wi-Fi/camera failures | Native app, multi-device offline verification, public validator |
| 5 — Volunteers/leaders, operational roster by 4 Oct; optional integrated work 3–8 Oct | Confirmed leaders/volunteers; core admission work staffed | Roster, shifts, briefing and scoped views if affordable | FR-15–18/AT-13; external roster acceptable with owner and rehearsal | Diverts effort from entry readiness | Open recruitment portal unless still needed; scoring, certificates, shift marketplace |
| 6 — Tasks and event operations, 5–11 Oct | Current team and approved schedule; can run in shared docs | Critical task board, cue sheet, incident/announcement process, dashboard/extract | AT-19; final schedule planned by 11 Oct per S05 §10 | Duplicated boards and stale cue versions | Workflow designer, chat platform, emergency dispatch |
| 7 — Speaker management, operational work now; optional tracker by 11 Oct | S05 review window 21 Sep–4 Oct; program lead, private storage | Sources/rights/rehearsal register, readiness evidence, approved public profiles | AT-20; 8–10 is target not fabricated database seed | Software distracts from editorial review | Speaker accounts, AI fact-check approval, full digital rights-management platform |
| 8 — Readiness, 12–18 Oct rehearsal; 19–20 Oct final checks | Critical tests, named operators/deputies, venue agreement | Full entry/outage/restore rehearsal, frozen release, local runbook, support rota, go/no-go record | All applicable P0 tests pass with evidence; unresolved critical failures block affected service | Last-minute migration or scope creep | New providers or features without incident-level review |

21 October: room access 12:00, public program 13:00–16:00, handover by 17:00 from local plans, subject to venue confirmation. The proposed 12:45 doors time remains C04. After event, complete FR-33 closeout: proposed survey 22–23 Oct, media review by 4 Nov, upload/closeout by 21 Nov; confirm current official instructions.

## Scope reduction gates

- **20 Sep:** if no named developer/backup or viable host/auth decision, select the public-site-plus-approved-external-registration route. Do not imply a custom platform can be delivered without capacity.
- **26 Sep:** if paid admission is required but merchant/provider/notice/refund decisions are unresolved, do not accept money. Organizer chooses an approved external route or revises the launch plan. Free admission is not an automatic fallback without approval.
- **4 Oct:** if integrated volunteers/tasks/speakers threaten core work, use approved shared documents and stop those custom modules. No duplicate writable roster.
- **11 Oct:** if concurrency/capacity/mobile/fallback tests fail, custom scanner is not approved for the door. Choose and rehearse a functioning provider/manual system; do not label an attractive mockup as readiness.
- **18 Oct:** feature freeze. Permit only reviewed fixes with affected regression tests and rollback path.
- **19–20 Oct:** rehearse the actual venue/devices/accounts/roster; restore test evidence must already exist. Do not make 12:00 on event day the first end-to-end test.

## Required reviewer evidence

Record requirement/test IDs, environment, real device versions, date, tester, result, issue link and sign-off. Organizer approves policy and operational readiness; Technology Lead signs technical evidence; relevant leader signs actual coverage. One person holding both roles records both responsibilities explicitly. Every failed critical test has remediation and retest evidence, not merely an accepted UI screenshot.

## Exact next phase

Review [decisions and questions](13-decisions-and-open-questions.md), then explicitly authorize Phase 1. Foundation may use synthetic data while public-language/venue content is being finalized, but privacy/host/storage constraints must be known before choosing services handling personal data. Registration launch and real data migration remain separate gates.
