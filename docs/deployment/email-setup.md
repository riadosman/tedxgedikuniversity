# Transactional email setup

The application has a database outbox and editable plain-text templates. No production sender account is selected, and no live recipient email was sent during this audit.

## Required provider configuration

Infrastructure operator obtains SMTP host/port, authenticated username/password or SMTP credential, verified sender and domain access. Configure SPF/DKIM/DMARC using the provider's actual values; none are invented here. Approve region/retention with the university/controller. Keep secrets outside source control/image.

Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS=true`, `DEFAULT_FROM_EMAIL` and the real HTTPS `PUBLIC_BASE_URL`. Production rejects development-only mail backends. Use authorized test inboxes for staging.

## Templates and localization

Email templates include registration-received/decision, ticket-issued/cancelled/access, volunteer-access/decision, account-invitation, attendee-invitation, announcement and schedule-update. Only `{event}`, `{name}`, `{link}`, `{status}` substitutions are allowed. No HTML or arbitrary attribute evaluation. Free approval issues a ticket confirmation; other decisions use decision messages. Password reset never removes MFA.

Attendee/volunteer notification language is saved and preserved in encrypted jobs. Add approved templates for every enabled language before intake. Missing templates become visible retry failures; the worker does not silently switch to English. Event facts and privacy/university wording require separate approval. Test links, status labels and line wrapping in real clients.

## Worker, retries and evidence

Schedule `python manage.py deliver_notifications --limit 50` every minute. Short database leases support multiple workers; SMTP has a timeout. Failures back off, stop after five attempts and expose only a redacted error class. Authorized staff retry failed jobs with a reason. Monitoring checks overdue messages and worker heartbeats.

Deduplication prevents duplicate queued business events. SMTP acceptance is recorded as sent, not guaranteed inbox delivery. A crash after SMTP acceptance but before saving can produce a duplicate email; exactly-once email is not claimed. Ticket issuance does not repeat with delivery retry. Provider bounce/delivery webhooks require the selected provider and are not invented.

Staging must exercise every template, correct recipient/language/event/link, refused credentials, timeout, missing template, duplicate enqueue and worker restart. Confirm sender DNS, provider logs, inbox/spam results and alert receipt separately. Those provider checks remain BLOCKED pending real configuration.
