# Backup, restore and troubleshooting

## Encrypted backup and isolated restore

Set a separate `BACKUP_KEY` generated with Fernet. Keep it and `CREDENTIAL_KEY` outside backup storage, with an approved recovery custodian. From the workspace root:

```powershell
.venv/Scripts/python.exe platform/scripts/backup.py create .local/backups/unique-release-name.enc
.venv/Scripts/python.exe platform/scripts/backup.py rehearse .local/backups/unique-release-name.enc
```

The first command creates an encrypted archive containing a PostgreSQL custom-format dump, private files and checksums/counts. It refuses to overwrite an existing backup. The rehearsal restores into a newly named database, validates table counts/files/admission uniqueness, and removes only that temporary database. It does not overwrite the live database. Quiesce writes when using count comparison: a live source can legitimately change after the dump snapshot. Production backup rotation, off-host transfer, continuous recovery and key custody are separate deployment responsibilities.

After a real disaster, restore into a separate environment and pause admission. Reconcile changes after the backup, including cancelled/replaced credentials, actual admissions and privacy erasures. Do not reuse restored credentials blindly or reopen on the basis of a healthy process alone. See the [entrance failure plan](../event-day/check-in-and-fallback.md).

## Common issues

| Symptom | Check / resolution |
|---|---|
| Holding page instead of event website | Event publication is still false. Review source/branding/policy before publishing |
| Registration unavailable | Check policy/notice approval, dates, capacity, enabled general ticket type, mode and free/paid decision |
| Staff account has no workspace | Assign an active, unexpired event role; volunteer acceptance alone creates no privileges |
| Repeated MFA failure | Check device time and fresh code; codes cannot be replayed. Use one-use recovery code if necessary |
| Privileged action requires verification | Reverify TOTP, then retry within the recent-MFA window |
| Email queued/failed | Run `deliver_notifications`; inspect redacted job status, template placeholders and SMTP configuration. Failed jobs can be retried after correcting the cause |
| File cannot download | It may be quarantined, archived or outside the user's scope. Configure the malware scanner; do not bypass quarantine |
| Scan request outcome unknown | Preserve the open page and retry the same request. If sign-in expired, reauthenticate separately and retry; otherwise use supervisor reconciliation |
| Invalid ticket or wrong event | Use current ticket link/reference; never override validation with a frontend flag |
| Local PostgreSQL unavailable | Run the isolated local helper; it binds port 55432 and preserves the existing Windows service. It refuses mismatched database URLs |
| Production HTTPS redirect loop | Correct trusted-proxy configuration and header stripping. Do not disable production security merely to hide the loop |
| Stale editor conflict | Reload the current record, review changes and submit a fresh version |
| Manual ledger rejected | Resolve unknown ticket/reference/time/duplicate row with supervisor. Import remains transactional |

Health endpoint `/health/` returns only service availability. `operations_health` reports redacted stale/failed email counts. Neither endpoint proves event staff readiness, legal approval or external-provider deliverability.
