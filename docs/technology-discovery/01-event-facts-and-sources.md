# 01 — Event facts, repository findings and source map

Status: evidence baseline, 17 September 2026. See [external verification](14-external-constraints.md) for current rules; see [decisions](13-decisions-and-open-questions.md) for resolutions still needed.

## Inspection method and boundaries

Recursively enumerated the workspace, including hidden files; checked root and ancestor instruction files; read both formatting-rule files, both Markdown event guides, event PDFs and relevant correspondence. Extracted the text-bearing PDFs; visually read all three pages of the image-only Turkish administrative checklist and all seven pages of the illustrated speaker guide. Inspected a contact sheet of all 26 raster assets and the named poster at full size. Artwork inspection is not a branding certification. External accounts and private university portals were not accessed. No inferred configuration was treated as an existing integration.

At inspection there were **41 files: 10 PDFs, 4 Markdown files, 1 text file, 25 PNGs and 1 JPG**. `git rev-parse --is-inside-work-tree` reported that the directory is not a Git repository. There were no package manifests, lockfiles, source directories, tests, build scripts, migrations, environment files, deployment definitions, API clients or CI definitions. No `AGENTS.md` was found in the workspace or inspected ancestors. See [inventory](repository-inventory.md).

| Area | Observation | Conclusion / limit |
|---|---|---|
| Event information | Root PDFs, root correspondence and guide, `Turkish Language/`, `arabic_guides/official_sources/` | There is no single `event/` source folder |
| Application stack | No executable project artifacts | No established frontend, backend, ORM or framework |
| Database/authentication | No schemas, migrations, account configuration or identity integration | Unknown whether something exists outside this workspace |
| Design | Poster, logo and certificate raster concepts | Assets are not a coded design system or approved template |
| Environment/integrations | Event-resource links in correspondence; no application config | TED account resources are not evidence of API integration |
| Requirements | Event checklists and 16 September tailored guide | Operational requirements exist; no prior technical specification/ADRs found |
| TODOs | Unchecked administrative lists, unnamed fifth manager, proposed tool workflows | Completion and assignment are unverified |
| Installed inspection tools | Python, PDF/image libraries used to read sources | Workstation tools do not establish a project stack |

Existing technical decisions: **none confirmed**. The root guide §5 explicitly labels its tools and automation as proposals, not configured systems. The newly requested platform is a product direction from the organizer, not an existing implementation.

## Source register

Paths are relative to the workspace root; these are private review links, not public-site content.

| ID | Path | Relevant locator and authority |
|---|---|---|
| S01 | [Mails.txt](../../Mails.txt) | `TEDx License Confirmation and Resources`, 24 Aug, lines 195–231; named event, date, tier, cap, expiry. Primary correspondence copy; signed licence/portal remains to be checked |
| S02 | [Mails.txt](../../Mails.txt) | `Julia Gross (TED)`, 17 Aug 2026 16:31 EDT; application approval, content, branding, survey, individual licence |
| S03 | [Mails.txt](../../Mails.txt) | `TEDx Licensing Team`, 28 Aug 2026 14:48 EDT; permission to read video script |
| S04 | [Mails.txt](../../Mails.txt) | 13 Aug review and 17 Aug organizer response, including lines 319–379; independence, university focus and candidate ideas |
| S05 | [Arabic detailed plan](<../../TEDxGedik University — الملف التفصيلي.pdf>) | 4 pages, updated 31 Aug; §§1–12; planning source, not completion evidence |
| S06 | [Arabic practical plan](<../../TEDxGedik University — خطة العمل العملية.pdf>) | 2 pages; preparation, event-day periods and post-event checklist |
| S07 | [Arabic administrative checklist](<../../TEDxGedik University — قائمة المهام الإدارية.pdf>) | 3 pages; proposed management distribution, governance, volunteers, production, finance |
| S08 | [Arabic introduction](<../../TEDxGedik University — Introduction.pdf>) | 2 pages; audience, purpose and planned format |
| S09 | [Arabic tailored guide](../../دليل%20تنظيم%20الفعاليات.md) | Updated 16 Sep; §§1–7, explicitly proposed eight-talk timetable and unresolved facts; synthesized planning document |
| S10 | [Turkish guide](<../../Turkish Language/دليل تنظيم الفعاليات.md>) | Translation of S09, not independent confirmation |
| S11 | `Turkish Language/` — Introduction, detailed, practical and administrative PDFs | Turkish counterparts, 1/2/2/3 pages respectively; administrative version visually inspected. Some versions summarize rather than reproduce every Arabic section |
| S12 | [Content guidelines](../../arabic_guides/official_sources/TEDx_Content_Guidelines_EN.pdf) | 9 pages; content, publication and fact-checking guidance; local snapshot, version/date not established |
| S13 | [Illustrated speaker guide](../../arabic_guides/official_sources/Illustrated_TEDx_Speaker_Guide_EN.pdf) | 7 illustrated pages; idea, outline, slides, rehearsal; adaptation, not a signed licence |
| S14 | [Poster concept](../../TEDx_Afis_Tasarimlari/Gemini_Generated_Image_h3i0pdh3i0pdh3i0.jpg) and other files in that folder | Text names Kartal conference hall and a different headline; registration QR areas are placeholders |
| S15 | `tedx_logo/`, `tedx_logo_from_files.png`, `TEDx_Sertifika_Tasarimlari/`, `TEDx_Sertifika_Tasarimlari_guncel/` | Logo/certificate visual concepts, placeholders; no documented final selection |
| S16 | [Formatting rules](../../قواعد%20إنشاء%20الملفات.md) and Turkish counterpart | File-production process only; not event facts |
| U01 | Organizer's current discovery request | Requester acts as Event Organizer and Technology Lead; requirements documentation only; no implementation |

## Source-supported facts and plans

| ID | Finding | Classification and source | System consequence |
|---|---|---|---|
| F01 | Licensed name in email is `TEDxGedik University` | Confirmed from S01 licence details; C01 remains | Store canonical name separately from URL slug; publication requires reconciliation |
| F02 | 21 October 2026; University type, Community tier, one event | Confirmed from S01 | Single-event implementation; do not build multi-tenant SaaS |
| F03 | Up to 100 attendees | Confirmed from S01/S02 | Hard ticket allocation ceiling; no oversubscription disguised as occupancy |
| F04 | Audience 13:00–16:00; team 12:00–17:00 | Documented plan S05 §3/S06 | Separate public schedule and private setup runbook |
| F05 | University location link is recorded | S05 header/§6; exact room conflicts with S14 | Venue publication gate; no inferred postal address or map coordinates |
| F06 | Riad Osman is organizer/licence contact; requester is technology lead | S01–S04/U01 | Organizer and technical roles may belong to one person but remain separate permissions |
| F07 | Permission to read opening-video script | Confirmed S03 | Store approval reference privately; opening content needs exact approved script |
| F08 | Main focus: students, faculty, researchers; selected other community voices | S04/S08 | Public audience copy and speaker curation; not student-only eligibility by inference |
| F09 | 8–10 talks and 2–3 reserves | Planning target S05 §§3–4/S07 | No invented speaker records or fixed count in public schedule |
| F10 | Talks up to 18 minutes in event correspondence | S02; S05 §3 | Validate event policy; do not generalize new web exceptions into this licence |
| F11 | “Ideas from where we stand” theme | Proposed S05 §2/S09 §1 | Draft content; not a confirmed public title |
| F12 | Tuka Al-Fallah: program; Atika: production/venue; Mahmoud Tabaq: audience; fifth manager unnamed | Proposed S07 first page/S11 administrative p1 | Seed no real permissions until assignments are approved; confirm Latin spellings |
| F13 | Sources/slides/rights/releases/rehearsal must be tracked | Documented workflow S05 §§4–5/S12/S13 | Separate public biography from internal evidence and readiness |
| F14 | Tasks, decisions, risk logs, deputies and short coordination meetings | Documented workflow S05 §7/S07 | Minimal roster, responsibilities and issue escalation; chat is not authoritative |
| F15 | No final admission price, ticket provider, registration URL or policy found | Unknown S05 §8/S09 §§1,5; S14 placeholder | Free is a proposal; no payment vendor selection |
| F16 | No approved total budget; contingency 10–15% suggested | S05 §7/S09 §3 | Budget limits and ongoing service cost need approval |
| F17 | Verify room access, exits, accessibility, sound, projection and connectivity | Planning tasks S05 §6/S06/S07 | Physical/network readiness not proved by documents |
| F18 | One group of attendees; no stage panel/Q&A in current plan | S05 §3 | No Q&A/voting module in baseline; preserve the planned format |
| F19 | Recording, rights review, survey and publication/archive workflow | S05 §9/S07 final page | Export approved data; track manual external completion; no fabricated TED API |
| F20 | Arabic and Turkish guides, Turkish posters, English certificates exist | S09–S15 | This is not evidence of approved site, scanner or talk languages |
| F21 | Licence valid for one event before 17 Aug 2027; renewal deadline stated | S01 lines 222–228 | Do not calculate expiry from 24 Aug email receipt |

Source-grounded dates: foundation tasks originally by 6 Sep; selection 7–20 Sep; drafts/review 21 Sep–4 Oct; runbook/registration/testing 5–11 Oct; full rehearsal/freeze 12–18 Oct; final inspection 19–20 Oct (S05 §10). Actual completion is unknown. S09's proposed post-event dates are 22–23 Oct survey, 4 Nov media review, 21 Nov closeout. No acceptance of these dates is inferred.

## Contradictions and resolution register

| ID | Conflicting evidence | Impact | Proposed treatment / owner |
|---|---|---|---|
| C01 | S01 says `TEDxGedik University`; S05/S08/S11 say `TEDx University Event`; U01 heading/S14 omit the space in `GedikUniversity` | Public identity, logo, domain and generated tickets | Use S01 as provisional canonical value; organizer confirms portal spelling and approves artwork before publication. Existing assets not changed |
| C02 | S05/S09: room unspecified; S14 names `Kartal Konferans Salonu` | Arrival, access, map, scanner rehearsal | Organizer/venue obtain written booking and exact room/address; artwork alone does not prove booking |
| C03 | S05 theme is a proposal; S14 headline is “Fikirlerin Geleceğe Açılan Kapısı” | Theme versus marketing tagline unclear | Program/organizer classify and approve each field; do not treat either as final theme |
| C04 | S05 says only advertise 13:00–16:00; S09 suggests 12:45 admission | Public instructions | Keep doors time unpublished until organizer/venue approves |
| C05 | S05/S07 plan 8–10 talks; S09 allocates eight 15-minute talks | Schedule allocation | S09 is an alternative draft, not a superseding approved schedule; program lead resolves |
| C06 | S04 organizer response says no outside sponsorship/affiliation; S05 §7 discusses sponsorship | Sponsor pages, finance and recognition | Organizer verifies event-specific commitment with TED before sponsorship features/content; generic rules do not resolve the correspondence |
| C07 | S05 general “one year from approval”; S01 explicitly says before 17 Aug 2027 | Renewal and asset ownership | Preserve explicit S01 date; confirm portal before renewal |
| C08 | Older wording can imply only occupancy at a moment is capped; current X02 says limit ticket distribution and keep one audience group | Ticket reuse/cancellation/exit | Proposed lifetime admission model in document 06; no replacement audience after checkout |
| C09 | S08 broadly excludes political/religious content; S05 §5/S12 distinguish agendas from discussion | Automated moderation could wrongly reject content | Human editorial review; no keyword ban presented as TED policy |
| C10 | S02 specifies an 18-minute limit; current official Rules allow some other formats beyond that length | Event timing and publication eligibility | Preserve the correspondence limit as proposed event policy; organizer verifies any requested exception. See X06 and document 14 |

None of these records silently edits existing documents or asserts that the organizer has resolved the issue.
