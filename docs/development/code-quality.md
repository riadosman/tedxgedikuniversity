# Code quality verification

Run from `platform/` after synchronizing the pinned development lock into the workspace `.venv`:

```powershell
../.venv/Scripts/python.exe -m ruff format --check .
../.venv/Scripts/python.exe -m ruff check .
../.venv/Scripts/python.exe -m mypy
../.venv/Scripts/python.exe scripts/translations.py --check
../.venv/Scripts/python.exe manage.py check
../.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
../.venv/Scripts/python.exe -m pytest -q
```

Mypy checks 60 application files with Django stubs and `check_untyped_defs`. Admission services, scanner request contract, payment interface, authorization, core transaction/audit helpers and redaction additionally reject missing function annotations, untyped calls, generic Any and Any returns. Scanner values are validated into a typed immutable object; cached responses are shape checked. Nullable model values are handled explicitly.

This is **not repository-wide strict typing**. Dynamic resource/form/view dispatch, management commands, scripts and tests still include unannotated framework boundaries; migrations are excluded. Completing that developer work requires typed resource/form interfaces and request/model narrowing with the existing workflow suite retained. Do not use broad ignores or blanket Any annotations just to obtain a green strict run.

The sustained check-in test uses an isolated PostgreSQL database and five workers. Run with `TEDX_LOAD_SECONDS=300` on an otherwise idle test host; thresholds are p95 <500 ms/p99 <1500 ms at the service boundary. A build running alongside one short run caused a 507.64 ms p95 miss; the subsequent isolated run passed. HTTP/device/network performance remains a separate gate.

Python production-lock and npm production-dependency audits found no known vulnerabilities on 17 September 2026. This is time-bounded dependency evidence, not proof of application security. Never run synthetic rehearsals against the real event database.
