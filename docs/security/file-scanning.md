# Private files and malware scanning

Uploads accept PDF/PPTX/PNG/JPEG up to 25 MB. Extension and signature are checked; PNG/JPEG images are decoded and pixel-limited. PPTX must contain a presentation, exclude macro/path traversal entries and remain within archive-count/expanded-size limits. Client MIME headers are not trusted. Generated storage paths prevent user-selected filenames. Linux files/directories use 0600/0700; verify actual mount ACLs.

Without `FILE_SCAN_COMMAND`, files remain quarantined. The setting contains a trusted executable/fixed arguments; a generated file path is appended without a shell. Exit 0 means clean, 1 means detected/rejected; other exit codes remain quarantined for operator repair. An always-success script is not a scanner. `python manage.py scan_documents --limit 25` verifies hashes and audits release/rejection. Timeouts/unavailable files remain quarantined. This command is infrastructure-operator only.

A configurable option is a maintained ClamAV installation with `FILE_SCAN_COMMAND="clamscan --no-summary"`, current signatures and monitored updates. It is not already installed/active by virtue of this documentation. Operator must install the engine, provide UID 10001 access, allocate resources and verify its current exit-code contract. Do not expose scanning daemons publicly. Test a harmless clean file and the official EICAR anti-malware fixture in isolated staging, never real malware. Record engine/signature versions and results. Mocked return-code tests do not count as live engine evidence.

Clean private files still require server-side leadership/department/task/speaker authorization. Archived/quarantined files cannot download. Public photos require clean public-candidate files referenced by an approved speaker snapshot. Private downloads are attachments with no-store; the media directory has no public route. Archive withdraws access, not physical backup copies. Approved disposal includes storage and backup custody.

Tests cover private access/quarantine, malformed uploads, denied-upload cleanup and changed-file rejection. Engine installation/signatures, EICAR and deployed permissions remain operating gates.

Verify engine options and limits against the [official ClamAV scanning guide](https://docs.clamav.net/manual/Usage/Scanning.html). Configure scan-size limits above the accepted upload/expanded-archive limits and treat encrypted or limit-exceeded content as a non-clean verdict; do not allow skipped files to be reported clean. Use the official EICAR test fixture only in controlled staging.
