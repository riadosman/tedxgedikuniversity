import pytest
from django.core.management import call_command
from core.models import AuditLog


@pytest.mark.django_db
def test_policy_drafts_preserve_approval_and_existing_content(event):
    event.published = False
    event.privacy_approved = False
    event.policy_approved = False
    event.registration_mode = "closed"
    event.privacy_notice = ""
    event.terms = ""
    event.notice_version = ""
    event.save()
    call_command("prepare_policy_drafts", slug=event.slug)
    event.refresh_from_db()
    assert "Yayın öncesi kurumsal doğrulama" in event.privacy_notice
    assert "Katılım ve Gönüllülük" in event.terms
    assert event.notice_version == "2026-09-17-draft-2"
    assert not event.privacy_approved and not event.policy_approved
    assert not event.published and not event.volunteer_open
    assert event.registration_mode == "closed"
    version = event.version
    event.privacy_notice = "Organizer revision"
    event.save()
    call_command("prepare_policy_drafts", slug=event.slug)
    event.refresh_from_db()
    assert event.privacy_notice == "Organizer revision"
    assert event.version == version
    assert AuditLog.objects.filter(event=event, action="event.policy_drafts.prepared").count() == 1
