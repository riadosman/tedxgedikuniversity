# Accessibility status

Scope: public/staff interfaces, forms, scanner, tables/navigation and language direction. This is not a WCAG compliance declaration.

Implemented: semantic headings/landmarks, labels, Django field errors, skip link, visible focus, keyboard-focusable main/table regions, scoped table headers, mobile menu expanded state, explicit scanner result wording and live status. Camera denial has a fallback. Scanner data uses textContent; templates escape content.

The expanded axe test found the dashboard's timed meta refresh. It was replaced by partial updates, pause checkbox and manual refresh. Focused content is not replaced, and failure identifies stale information. Forms focus the first invalid control. Language selection is labelled and explicitly submitted. RTL direction/CSS and translated controls are in place; event content remains separate.

Automated Chromium checks cover selected WCAG A/AA tags on home, scanner, dashboard, task list, incident form, reports, public registration/volunteer forms and Turkish/Arabic mobile dashboards. They check overflow and capture screenshots. Final results are recorded in the readiness checklist; failures are not waived by this document.

NOT TESTED: actual NVDA/VoiceOver/TalkBack operation, real touch/lighting, iOS camera behavior, all content at 200%/400% zoom, attachment accessibility and staff with access needs. Execute the device/keyboard/screen-reader matrix before event readiness. Organizers remain responsible for accessible approved content, maps, images and documents. Automated zero violations do not certify WCAG compliance.
