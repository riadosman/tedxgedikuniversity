"""Registration asks whether the attendee is an İstanbul Gedik University student; staff filter by it."""

import csv
import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from admissions.models import Attendee
from admissions.services import notice_digest
from core.models import PrivacyRequest
from core.privacy import anonymize_attendee

STUDENT, GUEST, EARLIER = "Ayse Ogrenci", "Mehmet Misafir", "Eski Kayit"


def data(event, **extra):
    return {
        "name": "Test Guest",
        "email": "guest@example.invalid",
        "phone": "+90 532 123 45 67",
        "gedik_student": "yes",
        "arrives_by_car": "no",
        "privacy": "on",
        "notice_version": event.notice_version,
        "notice_hash": notice_digest(event),
        **extra,
    }


def register(client, event, **extra):
    return client.post(reverse("register", args=[event.slug]), data(event, **extra))


@pytest.fixture
def staff(client, organizer, settings):
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    session = client.session
    session["mfa_at"] = timezone.now().timestamp()
    session.save()
    return client


@pytest.mark.django_db
def test_registration_form_asks_whether_gedik_student(client, event):
    page = client.get(reverse("register", args=[event.slug]))
    assert b'name="gedik_student"' in page.content


@pytest.mark.django_db
@pytest.mark.parametrize("answer, stored", [("yes", True), ("no", False)])
def test_registration_stores_gedik_student_answer(client, event, answer, stored):
    assert register(client, event, gedik_student=answer).status_code == 302
    assert Attendee.objects.get().gedik_student is stored


@pytest.mark.django_db
@pytest.mark.parametrize("answer", ["", "maybe"])
def test_registration_requires_gedik_student_answer(client, event, answer):
    response = register(client, event, gedik_student=answer)
    assert response.status_code == 200
    assert not Attendee.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "gedik, shown",
    [("yes", {STUDENT}), ("no", {GUEST}), ("unknown", {EARLIER}), ("", {STUDENT, GUEST, EARLIER})],
)
def test_staff_filter_attendees_by_gedik_student(client, event, staff, gedik, shown):
    event.capacity = 3
    event.save()
    register(client, event, name=STUDENT, email="student@example.invalid", gedik_student="yes")
    register(client, event, name=GUEST, email="guest@example.invalid", gedik_student="no")
    register(client, event, name=EARLIER, email="earlier@example.invalid")
    # Registered before the question existed.
    Attendee.objects.filter(name=EARLIER).update(gedik_student=None)
    listing = staff.get(reverse("resource-list", args=[event.slug, "attendees"]), {"gedik": gedik})
    assert listing.status_code == 200
    assert {name for name in (STUDENT, GUEST, EARLIER) if name.encode() in listing.content} == shown


@pytest.mark.django_db
def test_staff_export_includes_gedik_student(client, event, staff):
    register(client, event, gedik_student="yes")
    export = staff.post(
        reverse("resource-export", args=[event.slug, "attendees"]), {"reason": "Attendance statistics"}
    )
    header, row = list(csv.reader(io.StringIO(export.content.decode())))[:2]
    assert row[header.index("gedik_student")] == "yes"


@pytest.mark.django_db
def test_personal_data_download_includes_gedik_student(client, event):
    response = register(client, event, gedik_student="no")
    assert client.post(response.url, {"action": "export"}).json()["gedik_student"] is False


@pytest.mark.django_db
def test_anonymization_clears_gedik_student(client, event, organizer):
    register(client, event, gedik_student="yes")
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
    assert attendee.gedik_student is None
