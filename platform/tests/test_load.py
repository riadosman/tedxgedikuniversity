"""Configurable sustained load against isolated PostgreSQL, never the event database."""

import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
import pytest
from django.conf import settings
from django.db import connections
from admissions.services import check_in
from admissions.models import CheckIn
from .test_admission import allocate


@pytest.mark.django_db(transaction=True)
def test_sustained_admission_load(event, organizer):
    event.capacity = 100
    event.save()
    credentials = [allocate(event, organizer, f"load-{index}@example.invalid")[1] for index in range(100)]
    event.entry_mode = "online"
    event.save()
    duration = int(os.getenv("TEDX_LOAD_SECONDS", "2"))
    rate = 10
    total = max(20, duration * rate)

    def scan(index):
        started = time.perf_counter()
        try:
            result = check_in(event, organizer, request_id=uuid.uuid4(), credential=credentials[index % 100])
            return result["code"], time.perf_counter() - started
        finally:
            connections.close_all()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = []
        for index in range(total):
            due = started + index / rate
            delay = due - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            futures.append(pool.submit(scan, index))
        results = [future.result() for future in futures]
    latencies = sorted(seconds for _, seconds in results)
    new = sum(code == "VALID" for code, _ in results)
    assert new == min(total, 100)
    assert CheckIn.objects.filter(event=event).count() == new
    assert all(code in {"VALID", "ALREADY_CHECKED_IN"} for code, _ in results)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]
    report = {
        "duration_seconds": duration,
        "requests": total,
        "target_requests_per_second": rate,
        "clients": 5,
        "new_admissions": new,
        "p95_service_ms": round(p95 * 1000, 2),
        "p99_service_ms": round(p99 * 1000, 2),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "environment": "isolated local PostgreSQL; service boundary, excluding HTTP/network",
    }
    folder = Path(settings.ROOT_DIR) / ".local/test-artifacts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"load-{duration}s.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert p95 < 0.5, report
    assert p99 < 1.5, report
