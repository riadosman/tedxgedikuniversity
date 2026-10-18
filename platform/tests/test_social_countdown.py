"""Instagram and LinkedIn calls to action, and the days-left counter in the home hero."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from .test_registration_contact import register

INSTAGRAM = "https://www.instagram.com/tedxgedikuniversity/"
LINKEDIN = "https://www.linkedin.com/company/tedx-gedik-university/"


def starts_in(event, days):
    start = timezone.localtime() + timedelta(days=days)
    event.setup_at, event.admission_opens_at = start - timedelta(hours=1), start - timedelta(minutes=15)
    event.starts_at, event.ends_at = start, start + timedelta(hours=3)
    event.save()


@pytest.mark.django_db
def test_home_invites_visitors_to_follow_announcements(client, event):
    page = client.get(reverse("home")).content.decode()
    assert "All announcements are on Instagram" in page
    assert f'href="{INSTAGRAM}"' in page
    assert "mention TEDxGedik University" in page
    assert f'href="{LINKEDIN}"' in page


@pytest.mark.django_db
def test_public_footer_links_both_accounts(client, event):
    page = client.get(reverse("register", args=[event.slug])).content.decode()
    footer = page.split('class="public-footer"', 1)[1]
    assert f'href="{INSTAGRAM}"' in footer
    assert f'href="{LINKEDIN}"' in footer


@pytest.mark.django_db
def test_ticket_points_attendees_to_instagram_announcements(client, event):
    page = client.get(register(client, event).url).content.decode()
    assert "Event announcements are shared on Instagram." in page
    assert f'href="{INSTAGRAM}"' in page.split("Event announcements are shared on Instagram.", 1)[1]


@pytest.mark.django_db
@pytest.mark.parametrize("days", [40, 1])
def test_hero_counts_days_until_the_event(client, event, days):
    starts_in(event, days)
    page = client.get(reverse("home")).content.decode()
    assert "Days until the event" in page
    assert f'<span class="countdown-number">{days}</span>' in page


@pytest.mark.django_db
def test_hero_announces_the_event_day(client, event):
    starts_in(event, 0)
    page = client.get(reverse("home")).content.decode()
    assert "The event is today" in page
    assert "Days until the event" not in page


@pytest.mark.django_db
def test_hero_counter_disappears_after_the_event(client, event):
    starts_in(event, -2)
    page = client.get(reverse("home")).content.decode()
    assert "Days until the event" not in page
    assert "The event is today" not in page
