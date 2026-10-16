"""Public website redesign: TEDx-required copy, honest calls to action, content-driven program, style isolation."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from core.models import Page
from core.templatetags.ui import paragraphs, program_outline

DISCLAIMER = "This independent TEDx event is operated under license from TED."


def publish(event, key, title, body, language="en"):
    page, _ = Page.objects.get_or_create(
        event=event, key=key, language=language, defaults={"title": title, "body": body}
    )
    page.title, page.body = title, body
    page.published_snapshot = {"title": title, "body": body, "language": language, "version": 1}
    page.save()


@pytest.mark.django_db
def test_home_carries_the_required_tedx_copy_and_link(client, event):
    page = client.get(reverse("home")).content.decode()
    assert "What is TEDx?" in page
    assert "Our event is called TEDxGedik University, where x = independently organized TED event." in page
    assert 'href="https://www.ted.com/tedx"' in page
    assert DISCLAIMER in page.split('class="public-footer"', 1)[1]


@pytest.mark.django_db
def test_about_page_includes_about_ted_and_tedx(client, event):
    page = client.get(reverse("public-page", args=[event.slug, "about"])).content.decode()
    assert "About TEDx, x = independently organized event" in page
    assert "TED is a nonprofit, nonpartisan organization" in page


@pytest.mark.django_db
def test_hero_shows_the_event_theme_and_falls_back_to_the_name(client, event):
    assert f'class="home-hero-title">{event.name}</h1>' in client.get(reverse("home")).content.decode()
    event.theme = "From Ideas to Impact"
    event.save()
    assert 'class="home-hero-title">From Ideas to Impact</h1>' in client.get(reverse("home")).content.decode()


@pytest.mark.django_db
def test_registration_call_to_action_follows_the_intake_gate(client, event):
    page = client.get(reverse("home")).content.decode()
    assert "Free registration. Your ticket is issued immediately." in page
    event.closes_at = timezone.now() - timedelta(minutes=1)
    event.opens_at = timezone.now() - timedelta(days=2)
    event.save()
    page = client.get(reverse("home")).content.decode()
    assert "Free registration. Your ticket is issued immediately." not in page
    assert "Registration information" in page


@pytest.mark.django_db
def test_program_rows_come_from_published_program_text(client, event):
    publish(
        event,
        "program",
        "Program",
        "All times are Istanbul time.\n\n12:45–13:00 | Check-in and Welcome\n13:00–13:10 | Opening and Introduction",
    )
    for url in [reverse("home"), reverse("public-page", args=[event.slug, "program"])]:
        page = client.get(url).content.decode()
        assert "<h3>Check-in and Welcome</h3>" in page and "<h3>Opening and Introduction</h3>" in page
    program = client.get(reverse("public-page", args=[event.slug, "program"])).content.decode()
    assert "All times are Istanbul time." in program


def test_program_outline_keeps_notes_separate():
    outline = program_outline("Intro line.\n\n10:00-11:00 | Talks\n11:00–11:30 | Break\n\nSee you there.")
    assert outline["rows"] == [
        {"starts": "10:00", "ends": "11:00", "title": "Talks"},
        {"starts": "11:00", "ends": "11:30", "title": "Break"},
    ]
    assert outline["notes"] == ["Intro line.", "See you there."]
    assert program_outline("") == {"rows": [], "notes": []}
    assert paragraphs("One\r\n\r\nTwo\n\n\n") == ["One", "Two"]


@pytest.mark.django_db
def test_public_styles_never_load_on_staff_or_sign_in_pages(client, event, organizer, settings):
    assert "public.css" in client.get(reverse("home")).content.decode()
    assert "public.css" in client.get(reverse("register", args=[event.slug])).content.decode()
    assert "public.css" not in client.get(reverse("login")).content.decode()
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    dashboard = client.get(reverse("dashboard", args=[event.slug]))
    assert dashboard.status_code == 200 and "public.css" not in dashboard.content.decode()


@pytest.mark.django_db
def test_contact_and_faq_text_links_are_clickable(client, event):
    publish(event, "faq", "FAQ", "How can I contact the team?\nEmail team@example.invalid.")
    page = client.get(reverse("public-page", args=[event.slug, "faq"])).content.decode()
    assert 'href="mailto:team@example.invalid"' in page


@pytest.mark.django_db
def test_team_members_reach_the_site_only_through_publication(client, event, organizer):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import PermissionDenied

    from core.models import RoleGrant
    from core.workflows import action_resource
    from team.models import TeamMember

    member = TeamMember.objects.create(
        event=event, name="Test Organizer", role="Organizer", biography="Synthetic test biography."
    )
    team_url = reverse("public-page", args=[event.slug, "team"])
    assert "Test Organizer" not in client.get(team_url).content.decode()
    editor = get_user_model().objects.create_user("team-editor")
    RoleGrant.objects.create(event=event, user=editor, role="editor", reason="Test")
    with pytest.raises(PermissionDenied):
        action_resource(event, editor, "team-members", member.pk, "publish", "Not allowed")
    action_resource(event, organizer, "team-members", member.pk, "publish", "Introduce the organizer")
    member.refresh_from_db()
    member.biography = "Unpublished draft edit."
    member.save()
    for url in [team_url, reverse("public-page", args=[event.slug, "about"])]:
        page = client.get(url).content.decode()
        assert "Test Organizer" in page and "Synthetic test biography." in page
        assert "Unpublished draft edit." not in page
    action_resource(event, organizer, "team-members", member.pk, "withdraw", "Hide for now")
    assert "Test Organizer" not in client.get(team_url).content.decode()
