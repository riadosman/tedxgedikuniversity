# 14 — External constraints and authoritative verification

Checked: **17 September 2026**. Public official pages were inspected; private TED account/contract details, university event approval and vendor agreements were not accessed. Local snapshots and emails remain source evidence, but their applicability is not silently broadened. No external message was sent and no account was changed.

## Responsibility boundary

| Party | Evidence-supported provision / responsibility | Not assumed |
|---|---|---|
| TED / TEDx resources | Licence and guidance; official event-page/organizer tools referenced in S01; documented media/survey processes below | A custom website, payment gateway, attendee QR scanner, volunteer application, event database or public integration API |
| Event Organizer | Canonical details, scope, editorial approvals, licence communications, operational policies and official-tool submissions | That the licence belongs to the university or a sponsor |
| University | Must be asked to confirm applicable institutional processes, room permissions, brand/visitor/filming/privacy contacts | Free hosting, SSO, email, Wi-Fi reliability, controller role or an approved venue merely because the event is university-based |
| Venue | Must confirm booking, access, physical capacity, accessibility, emergency arrangements and technical conditions | That a software attendance counter establishes legal/safe occupancy |
| Technology team | Build/configure the approved site, data flows, authentication, scanner, monitoring, backups and handover | Authority to choose merchant/privacy terms or publish unapproved content |

## Verification register

| ID | Authority and locator | Verified finding (limited summary) | Project action / unresolved part |
|---|---|---|---|
| X01 | [TEDx Rules](https://www.ted.com/tedx/before-you-apply/tedx-rules), Branding + Naming / Web + Social | Use full licensed name and independent positioning; site has mandatory TEDx/About/footer content and restrictions on homepage sponsors | Reconcile C01 and obtain canonical public revision; copy approved official text during implementation, not draft from memory |
| X02 | [Invite and engage attendees](https://www.ted.com/tedx/organizer-guide/invite-and-engage-attendees), Ticketing + inviting attendees; Rules, Attendance | Admission methods can differ; distribution must stay within licensing limits; event-specific email cap is 100 | Q01/Q03 decide eligibility/counting/re-entry; no 100-person “rotation” policy inferred |
| X03 | [Design and promote event](https://www.ted.com/tedx/organizer-guide/design-and-promote-event), Online presence / Create your website | Official event-page maintenance and an organizer's own website are distinct; website requires approved identity/content, separate sponsor recognition and no advertising | Organizer supplies official event URL and approved domain/account ownership; no hosted custom site or CMS API verified |
| X04 | [Invite and engage attendees](https://www.ted.com/tedx/organizer-guide/invite-and-engage-attendees), Collect attendee information / Communicate regularly | Guide describes permission-aware attendee survey information and a post-event uploader link | Review exact current survey fields and approved transfer basis in organizer account before export; no automatic bulk upload assumed |
| X05 | [Film, photograph and stream](https://www.ted.com/tedx/organizer-guide/film-photograph-and-stream), Upload your talks | Media Uploader is documented for publication to official TEDx channel; organizer/team access is via TED profiles | Manual handoff by authorized organizer; confirm account access, metadata, rights and timeline; no API invented |
| X06 | S03 opening permission; [TEDx Rules](https://www.ted.com/tedx/before-you-apply/tedx-rules), Event Basics | General opening-video rule differs from this event's explicit read-aloud permission | Preserve private approval and exact script. New/general format exceptions do not automatically amend the event's 18-minute correspondence |
| X07 | [KVKK Law 6698](https://www.kvkk.gov.tr/Icerik/6649/Personal-Data-Protection-Law), Articles 4–12; [transfer guide](https://www.kvkk.gov.tr/Icerik/8143/Kisisel-Verilerin-Yurt-Disina-Aktarilmasi-Rehberi) | Legal framework includes processing grounds, notices, rights, security and cross-border transfer conditions; Article 9 was amended | Q08: qualified controller/privacy review of each database, email, storage, identity, backup and TED recipient; no assumption ordinary checkbox consent authorizes all cloud transfers |
| X08 | [Gedik university privacy-notice index](https://www.gedik.edu.tr/ogrenciler/aday-ogrenciler/kvkk-aydinlatma-metinleri) | University publishes notices for specified processes; the inspected page is for prospective students | Event-specific controller, filming/visitor/minor policy, network and venue approvals remain unknown; do not reuse unrelated notice as event authorization |
| X09 | Approved venue / university representative; no written agreement in inspected files | Public PDFs and artwork are planning evidence only | Obtain room booking, precise address, counted occupancy, access/setup, power/network and emergency contact before final runbook |
| X10 | Prospective payment/ticketing provider official contract/documentation — provider not selected | Not yet verifiable | Validate Türkiye merchant eligibility, supported currency, settlement, fees, refunds, disputes, data locations, webhook auth/idempotency, cap behavior, exports and scanner capabilities before selection |
| X11 | [TEDx Organizer Guide](https://www.ted.com/tedx/organizer-guide), content/program sections; S12/S13 | Local speaker resources support staged preparation and evidence review; current guide is available | Program lead checks current content/rights/release versions; source snapshot is not automatically the latest policy |

The summaries above deliberately do not reproduce full official policy or template language. Store verification date and approval reference for the precise version used by the implementation.

## Additional policy differences to resolve visibly

- **C10 — general format guidance vs event correspondence:** current Rules “TEDx talk format” mentions some longer formats; S02 explicitly says this event's talks should not exceed 18 minutes. Proposed event policy remains 18 minutes unless the organizer obtains an applicable clarification. This is not permission to schedule longer talks.
- **Opening exception:** the public Rules page describes showing the introduction video; S03 explicitly permits this event to read its script. The evidence supports that narrow exception, not a replacement video or an exemption from unrelated content requirements.
- **Official copy versions:** the current Rules and design guide present differently worded TEDx descriptive copy. Publisher must select the current organizer-approved template and verify its meaning for this event; avoid inventing a blanket free-ticket claim from generic speaker-participation wording.
- **Sponsorship:** public general guidance does not itself resolve C06's event-specific no-outside-sponsorship response. Keep sponsor modules/content disabled pending Q13.

## Technical sources supporting proposed design

These are capability references, not proof of deployed features or approved vendors.

| Ref | Official source / inspected topic | Design use |
|---|---|---|
| XT01 | [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html), row locks and deadlocks | Document 06 serialization/lock ordering; independently test every mutation path |
| XT02 | [Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/) | Baseline staff identity/groups; custom event/object authorization still required |
| XT03 | [Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/) | Atomic persistence of ticket/admission/audit/outbox |
| XT04 | [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) | Production configuration review; no claim of automatic secure deployment |
| XT05 | [Next.js authentication guide](https://nextjs.org/docs/app/guides/authentication) | Alternative architecture evaluation; not an existing stack |
| XT06 | [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia) | Camera permission/HTTPS and failure handling; actual compatibility must be tested |
| XT07 | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Accessibility target and manual verification |
| XT08 | [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Deny-by-default, request/object scope and authorization test design |

## External-provider evaluation checklist

Before approving any ticketing/hosting/email/identity provider, record official documentation URL/date, account owner, region and subprocessors, expected recurring/usage costs, export and exit procedure, supported authentication, availability/backup features and tested failure behavior. Payment providers add the X10 checks. Do not sign up, purchase, transmit attendee data or claim capabilities based on a product name alone.
