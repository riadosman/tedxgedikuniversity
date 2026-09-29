"""Navigation, presentation queries and upload orchestration preserve existing boundaries."""

import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import RoleGrant
from core.views import navigation
from core.navigation import workspace_groups
from program.models import Speaker
from documents.models import Document
from tests.test_admission import allocate


@pytest.mark.django_db
def test_all_authorized_tools_remain_reachable(event, organizer, client, settings):
    settings.MFA_REQUIRED = False
    items = navigation(organizer, event)
    groups = workspace_groups(event, items, can_settings=True, can_reports=True)
    assert {key for key, _ in items} <= {link["key"] for group in groups for link in group["links"]}
    client.force_login(organizer)
    for group in groups:
        assert client.get(group["url"]).status_code == 200
    user = get_user_model().objects.create_user("gate-test")
    RoleGrant.objects.create(event=event, user=user, role="checkin", reason="Test")
    client.force_login(user)
    assert client.get(reverse("workspace-group", args=[event.slug, "people"])).status_code == 404
    assert client.get(reverse("scanner", args=[event.slug])).status_code == 200


@pytest.mark.django_db
def test_people_status_filters_and_computed_sort_are_safe(event, organizer, client, settings):
    settings.MFA_REQUIRED = False
    ticket, _ = allocate(event, organizer)
    client.force_login(organizer)
    url = reverse("resource-list", args=[event.slug, "attendees"])
    response = client.get(url, {"q": ticket.reference, "attendance": "no", "sort": "admitted_at"})
    assert response.status_code == 200
    assert response.context["page"].paginator.count == 1
    assert client.get(url, {"attendance": "yes"}).context["page"].paginator.count == 0
    response = client.get(url, {"status": "rejected"})
    assert response.context["page"].paginator.count == 0


@pytest.mark.django_db
def test_contextual_photo_upload_keeps_quarantine_and_version_checks(
    event, organizer, client, settings, tmp_path
):
    settings.MFA_REQUIRED = False
    settings.MEDIA_ROOT = tmp_path
    settings.FILE_SCAN_COMMAND = ""
    speaker = Speaker.objects.create(event=event, name="Photo fixture")
    client.force_login(organizer)
    url = reverse("speaker-photo", args=[event.slug, speaker.pk])

    def upload(version):
        image = io.BytesIO()
        Image.new("RGB", (20, 20)).save(image, format="PNG")
        return client.post(
            url,
            {
                "speaker_version": version,
                "title": "Test portrait",
                "scope": "public_candidate",
                "file": SimpleUploadedFile("portrait.png", image.getvalue(), "image/png"),
            },
        )

    assert upload(speaker.version).status_code == 302
    speaker.refresh_from_db()
    assert speaker.photo.scan_status == "quarantined"
    assert speaker.published_snapshot == {}
    original = speaker.photo_id
    count = Document.objects.count()
    response = upload(speaker.version - 1)
    assert response.status_code == 200
    assert response.context["form"].errors
    speaker.refresh_from_db()
    assert speaker.photo_id == original
    assert Document.objects.count() == count
    assert len(list(tmp_path.rglob("*.png"))) == 1
    user = get_user_model().objects.create_user("own-speaker")
    RoleGrant.objects.create(event=event, user=user, role="speaker", reason="Test")
    speaker.user = user
    speaker.save()
    client.force_login(user)
    assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_interface_languages_remain_available_without_event_content_settings(event, client):
    event.enabled_languages = []
    event.save()
    for language, direction in [("en", "ltr"), ("tr", "ltr"), ("ar", "rtl")]:
        response = client.get("/", {"lang": language})
        assert response.status_code == 200
        assert f'dir="{direction}"' in response.content.decode()
        assert len(response.context["interface_languages"]) == 3


@pytest.mark.django_db
def test_pagination_preserves_attendee_filters(event, organizer, client, settings):
    from admissions.models import Attendee, Registration

    settings.MFA_REQUIRED = False
    for index in range(31):
        attendee = Attendee.objects.create(
            event=event,
            name=f"Filter fixture {index}",
            email=f"filter-{index}@example.invalid",
            notice_version="test-1",
        )
        Registration.objects.create(event=event, attendee=attendee)
    client.force_login(organizer)
    response = client.get(
        reverse("resource-list", args=[event.slug, "attendees"]),
        {"q": "Filter", "status": "submitted", "attendance": "no", "sort": "name"},
    )
    assert response.context["page"].has_next()
    assert (
        "q=Filter&amp;status=submitted&amp;attendance=no&amp;sort=name&amp;page=2"
        in response.content.decode()
    )


@pytest.mark.django_db
def test_registration_screen_respects_existing_opening_window(event, client):
    from datetime import timedelta
    from django.utils import timezone

    event.opens_at = timezone.now() + timedelta(minutes=10)
    event.save()
    response = client.get(reverse("register", args=[event.slug]))
    assert response.context["closed"]
    assert response.context["registration_upcoming"]
    assert 'name="email"' not in response.content.decode()
