import pytest
from django.core.management import call_command
from django.urls import reverse
from core.models import Page
from admissions.models import Registration
from team.models import VolunteerApplication


@pytest.mark.django_db
def test_local_preview_pages_are_bilingual_and_read_only(client, event, settings):
    settings.DEBUG = True
    settings.PRODUCTION = False
    settings.LOCAL_EVENT_PREVIEW = True
    event.published = False
    event.volunteer_open = True
    event.save()
    call_command("prepare_public_content", slug=event.slug)
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "tr"
    for key in ["about", "theme", "venue", "program", "speakers", "faq", "contact", "privacy", "terms"]:
        response = client.get(reverse("public-page", args=[event.slug, key]))
        assert response.status_code == 200, key
        assert b'lang="tr"' in response.content
        assert "Yerel ön izleme" in response.content.decode()
        assert Page.objects.get(event=event, key=key, language="tr").title in response.content.decode()
    for route in ["register", "volunteer-apply", "recover", "volunteer-recover"]:
        assert client.get(reverse(route, args=[event.slug])).status_code == 200
    assert client.get(reverse("home")).status_code == 200
    client.cookies.clear()
    shared = client.get(reverse("home") + "?lang=tr")
    assert b'lang="tr"' in shared.content
    assert shared.cookies[settings.LANGUAGE_COOKIE_NAME].value == "tr"
    client.post(
        reverse("register", args=[event.slug]),
        {"name": "Test", "email": "test@example.invalid", "privacy": "on"},
    )
    client.post(
        reverse("volunteer-apply", args=[event.slug]),
        {"name": "Test", "email": "test@example.invalid", "privacy": "on", "availability": "Test"},
    )
    assert not Registration.objects.exists() and not VolunteerApplication.objects.exists()
    event.refresh_from_db()
    assert event.published is False
    assert not Page.objects.filter(event=event).exclude(published_snapshot={}).exists()


@pytest.mark.django_db
def test_production_never_uses_local_preview(client, event, settings):
    event.published = False
    event.save()
    settings.DEBUG = True  # Even a mis-set DEBUG cannot override the production guard.
    settings.PRODUCTION = True
    settings.LOCAL_EVENT_PREVIEW = True
    assert client.get(reverse("register", args=[event.slug])).status_code == 404
    assert client.get(reverse("public-page", args=[event.slug, "venue"])).status_code == 404


@pytest.mark.django_db
def test_content_preparation_preserves_edits_and_is_idempotent(event):
    call_command("prepare_public_content", slug=event.slug)
    page = Page.objects.get(event=event, key="about", language="tr")
    page.body = "Organizer edit"
    page.save()
    call_command("prepare_public_content", slug=event.slug)
    page.refresh_from_db()
    assert page.body == "Organizer edit"
    assert Page.objects.filter(event=event).count() == 36
