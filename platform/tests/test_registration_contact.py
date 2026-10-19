"""Registration phone, car and parking plate; attendance rules on registration and ticket."""

import csv
import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from admissions.models import Attendee, Ticket
from admissions.services import notice_digest
from core.models import Page, PrivacyRequest
from core.privacy import anonymize_attendee


def data(event, **extra):
    return {
        "name": "Test Guest",
        "email": "guest@example.invalid",
        "phone": "+90 532 123 45 67",
        "gedik_student": "no",
        "arrives_by_car": "no",
        "privacy": "on",
        "notice_version": event.notice_version,
        "notice_hash": notice_digest(event),
        **extra,
    }


def register(client, event, **extra):
    return client.post(reverse("register", args=[event.slug]), data(event, **extra))


def publish_rules(event, body="No entry or exit while a talk is in progress."):
    return Page.objects.create(
        event=event,
        key="rules",
        language="en",
        title="Attendance rules",
        body=body,
        published_snapshot={"title": "Attendance rules", "body": body},
        published_at=timezone.now(),
    )


@pytest.mark.django_db
def test_registration_stores_phone_and_car_answer(client, event):
    assert register(client, event).status_code == 302
    attendee = Attendee.objects.get()
    assert attendee.phone == "+90 532 123 45 67"
    assert attendee.arrives_by_car is False
    assert attendee.vehicle_plate == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad",
    [
        {"phone": ""},
        {"phone": "12345"},
        {"phone": "call me maybe"},
        {"phone": "90+532 123 45 67"},
        {"arrives_by_car": ""},
        {"arrives_by_car": "yes", "vehicle_plate": ""},
        {"arrives_by_car": "yes", "vehicle_plate": "34 ABC 123 / x"},
    ],
)
def test_registration_requires_valid_phone_car_answer_and_plate(client, event, bad):
    response = register(client, event, **bad)
    assert response.status_code == 200
    assert not Attendee.objects.exists() and not Ticket.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "typed, stored",
    [("34abc123", "34 ABC 123"), ("  06 a 1234 ", "06 A 1234"), ("34-ab-987", "34 AB 987")],
)
def test_plate_is_normalized_when_arriving_by_car(client, event, typed, stored):
    assert register(client, event, arrives_by_car="yes", vehicle_plate=typed).status_code == 302
    attendee = Attendee.objects.get()
    assert attendee.arrives_by_car is True
    assert attendee.vehicle_plate == stored


@pytest.mark.django_db
def test_plate_is_discarded_when_not_arriving_by_car(client, event):
    assert register(client, event, arrives_by_car="no", vehicle_plate="34 ABC 123").status_code == 302
    assert Attendee.objects.get().vehicle_plate == ""


@pytest.mark.django_db
def test_ticket_shows_plate_rules_and_door_time(client, event):
    publish_rules(event)
    response = register(client, event, arrives_by_car="yes", vehicle_plate="34 abc 123")
    page = client.get(response.url)
    doors = timezone.localtime(event.admission_opens_at).strftime("%H:%M")
    assert b"34 ABC 123" in page.content
    assert b"No entry or exit while a talk is in progress." in page.content
    assert f"Doors open at {doors}".encode() in page.content


@pytest.mark.django_db
def test_registration_page_shows_published_rules_and_door_time(client, event):
    publish_rules(event)
    page = client.get(reverse("register", args=[event.slug]))
    doors = timezone.localtime(event.admission_opens_at).strftime("%H:%M")
    assert b"No entry or exit while a talk is in progress." in page.content
    assert f"Doors open at {doors}".encode() in page.content


@pytest.mark.django_db
def test_unpublished_rules_stay_hidden(client, event):
    Page.objects.create(event=event, key="rules", language="en", title="Draft", body="Draft rule text")
    assert b"Draft rule text" not in client.get(reverse("register", args=[event.slug])).content


@pytest.mark.django_db
def test_personal_data_download_includes_phone_and_plate(client, event):
    response = register(client, event, arrives_by_car="yes", vehicle_plate="34 ABC 123")
    exported = client.post(response.url, {"action": "export"}).json()
    assert exported["phone"] == "+90 532 123 45 67"
    assert exported["arrives_by_car"] is True
    assert exported["vehicle_plate"] == "34 ABC 123"


@pytest.mark.django_db
def test_staff_export_and_search_include_phone_and_plate(client, event, organizer, settings):
    settings.MFA_REQUIRED = False
    register(client, event, arrives_by_car="yes", vehicle_plate="34 ABC 123")
    client.force_login(organizer)
    session = client.session
    session["mfa_at"] = timezone.now().timestamp()
    session.save()
    listing = client.get(reverse("resource-list", args=[event.slug, "attendees"]), {"q": "34 ABC 123"})
    assert listing.status_code == 200 and b"+90 532 123 45 67" in listing.content
    export = client.post(
        reverse("resource-export", args=[event.slug, "tickets"]), {"reason": "Parking reservation"}
    )
    rows = list(csv.reader(io.StringIO(export.content.decode())))
    header, row = rows[0], rows[1]
    assert header[:5] == ["name", "email", "phone", "arrives_by_car", "vehicle_plate"]
    # A leading "+" is a spreadsheet formula prefix, so the export escapes it.
    assert row[2:5] == ["'+90 532 123 45 67", "yes", "34 ABC 123"]


@pytest.mark.django_db
def test_anonymization_clears_phone_and_plate(client, event, organizer):
    register(client, event, arrives_by_car="yes", vehicle_plate="34 ABC 123")
    attendee = Attendee.objects.get()
    event.registration_mode = "closed"
    event.admission_opens_at = None
    event.starts_at = timezone.now() - timedelta(days=100, hours=3)
    event.ends_at = timezone.now() - timedelta(days=100)
    event.retention_days = 90
    event.retention_reason = "Survey completed; event dispute period reviewed"
    event.save()
    item = PrivacyRequest.objects.create(event=event, email=attendee.email, kind="erase", status="verified")
    anonymize_attendee(event, organizer, item.pk, "Verified request, retention elapsed")
    attendee.refresh_from_db()
    assert attendee.phone == "" and attendee.vehicle_plate == "" and attendee.arrives_by_car is None
