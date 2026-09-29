from datetime import timedelta
from unittest.mock import patch
import pytest
from django.utils import timezone, translation
from communications.models import Notification, NotificationTemplate
from communications.services import enqueue, deliver_batch
from core.monitoring import operational_health, heartbeat
from admissions.models import Attendee


@pytest.mark.django_db
def test_localized_delivery_retry_and_redacted_error(event, settings, mailoutbox):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    event.enabled_languages = ["en", "tr"]
    event.save()
    Attendee.objects.create(
        event=event,
        name="Test",
        email="locale@example.invalid",
        notice_version="test-1",
        notification_language="tr",
    )
    NotificationTemplate.objects.create(
        event=event, key="localized", language="tr", subject="Kayıt bilgisi", body="Merhaba {name}: {status}"
    )
    with translation.override("en"):
        job = enqueue(
            event,
            "locale@example.invalid",
            "localized",
            {"name": "Test", "status": "confirmed"},
            "locale-job",
        )
    with patch(
        "communications.services.EmailMessage.send", side_effect=ConnectionError("private SMTP reply")
    ):
        assert deliver_batch() == 0
    job.refresh_from_db()
    assert job.status == "pending" and job.last_error_code == "ConnectionError"
    Notification.objects.filter(pk=job.pk).update(next_attempt_at=timezone.now())
    assert deliver_batch() == 1
    assert len(mailoutbox) == 1 and mailoutbox[0].subject == "Kayıt bilgisi"
    assert deliver_batch() == 0


@pytest.mark.django_db
def test_scheduled_notifications_are_not_stale_and_dead_jobs_are(event, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setenv("MIN_FREE_STORAGE_BYTES", "1")
    monkeypatch.setenv("EXPECT_BACKGROUND_JOBS", "true")
    job = enqueue(event, "test@example.invalid", "future", {"name": "Test"}, "scheduled")
    Notification.objects.filter(pk=job.pk).update(
        created_at=timezone.now() - timedelta(days=2), next_attempt_at=timezone.now() + timedelta(days=1)
    )
    assert operational_health()["stale_email_jobs"] == 0
    assert operational_health()["jobs_ok"] is False
    heartbeat("email")
    heartbeat("maintenance")
    assert operational_health()["jobs_ok"] is True
    (tmp_path / ".runtime" / "email.json").write_text('{"completed_at": 1}', encoding="utf-8")
    assert operational_health()["jobs_ok"] is False  # Copying an old heartbeat cannot make it healthy.
    Notification.objects.filter(pk=job.pk).update(next_attempt_at=timezone.now() - timedelta(minutes=6))
    assert operational_health()["stale_email_jobs"] == 1


@pytest.mark.django_db
def test_missing_localized_template_fails_visibly(event, settings):
    event.enabled_languages = ["ar", "en"]
    event.save()
    with translation.override("ar"):
        job = enqueue(event, "test@example.invalid", "unconfigured", {"name": "Test"}, "missing-template")
    assert deliver_batch() == 0
    job.refresh_from_db()
    assert job.last_error_code == "DoesNotExist" and job.status == "pending"
