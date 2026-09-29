# Monitoring and alert response

Public `/health/` exposes only ok/unavailable and checks PostgreSQL. Probe the actual HTTPS domain every 30 seconds and alert the technology lead after repeated failures. External probes, alert channel and named recipients still require configuration.

Run `python manage.py operations_health` from the protected runtime environment each minute. Redacted JSON reports database latency, overdue/failed email jobs, storage, recent rejected scans, job heartbeat ages and optional backup freshness. Nonzero exit is unhealthy. Future scheduled emails are not overdue. With `EXPECT_BACKGROUND_JOBS=true`, email heartbeat must be within five minutes and maintenance within two hours; this detects a stopped scheduler even with an empty queue.

Configure `MIN_FREE_STORAGE_BYTES` (default 1 GiB), `BACKUP_DIRECTORY` and `BACKUP_MAX_AGE_SECONDS`. Use an approved tighter threshold during the critical entrance window. A fresh local archive does not prove an off-host copy exists. Monitor scanner signature freshness using the chosen engine's own check.

Aggregate structured request logs by route, status, duration and request ID. Alert on 5xx, sustained latency, authentication/MFA throttling, unexpected QR rejection spikes and entrance-mode failures. Never log request bodies, cookies, raw QR, private links or attendee addresses. Configure the reverse proxy to redact token-bearing URLs; supplied Gunicorn disables raw access logs. Restrict log access and retention.

Actionable baseline: failed health probes, any failed email, overdue lease, missing heartbeat, stale backup or low storage. A scan rejection spike requires entrance investigation, never automatic admission. Record incident, affected devices, time, request IDs and remediation. Verify actual alert receipt/escalation before launch: CLI output alone does not prove deployed monitoring.
