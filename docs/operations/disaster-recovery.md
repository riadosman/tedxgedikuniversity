# Disaster recovery

## Ownership, frequency and custody

Name recovery lead/deputy, encrypted backup location, off-host destination, key custodians and image/migration version. No hosting destination or approved retention is invented. Proposed baseline: daily backup plus a verified five-minute critical-window backup/PITR process. Approve and measure actual RPO/RTO in staging. Apply the privacy retention schedule and documented holds.

Archive contains PostgreSQL custom dump, private files and checksum/table-count manifest encrypted with `BACKUP_KEY`. Keep that key separate from archives. Preserve `CREDENTIAL_KEY`, Django secret and database/email/storage configuration in the secret manager. A dump is not secret recovery. Backup buffers the archive in memory; test expected file volume and RAM. Quiesce writes/uploads for a consistent checkpoint; the helper is not a distributed snapshot or PITR engine.

## Create and rehearse

From the workspace root (Linux uses the environment's `python`):

```powershell
.venv/Scripts/python.exe platform/scripts/backup.py create PRIVATE_BACKUP_PATH.enc
.venv/Scripts/python.exe platform/scripts/backup.py rehearse PRIVATE_BACKUP_PATH.enc
```

Creation refuses an existing output file. Copy off-host, verify checksum and restrict access. Rehearsal creates a new disposable database, verifies table counts, file hashes and admission uniqueness, then removes only its own database. Repeat after schema/storage changes. An empty-file restore does not establish private-file recovery.

## Retain a verified recovery

1. Pause public writes and workers. Coordinate the supervisor's manual ledger; record unresolved scan IDs and admission/revocation changes after the backup.
2. Provision protected PostgreSQL with permission to create a NEW database. Retrieve secrets; configure `DATABASE_URL` and verified remote TLS via `DB_SSLMODE`.
3. Choose a new `tedx_recovery_*` database name and empty private directory:

```powershell
.venv/Scripts/python.exe platform/scripts/backup.py restore PRIVATE_BACKUP_PATH.enc --database tedx_recovery_rehearsal --media-root NEW_EMPTY_PRIVATE_DIRECTORY
```

4. The helper refuses overwrite/nonempty media, verifies manifest and retains restored database/files. Match the image/migrations, run security/health checks, test restricted downloads/logins and decrypt a synthetic credential with the recovered key. Reapply later erasures/revocations and reconcile physical admissions before reopening.
5. Change application connections/media to the verified copies and restart workers. Record cutover. Keep entrance reconciling until the supervisor signs off, then brief all desks and resume online. Retain the old environment until signed off; never run two writable event states.
6. On failure keep the current production connection unchanged. Failed restore drops its newly created database. Inspect partial media and remove only the verified directory created for this recovery. Never reverse data migrations or overwrite the live database casually.

Local audit tests disposable and retained file-bearing recovery separately. Off-host loss, real key-custodian access, deployed RPO/RTO and physical venue outage remain external rehearsal requirements.
