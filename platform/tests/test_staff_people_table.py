"""The staff attendee and ticket tables show each value under its own heading."""

import re

import pytest
from django.urls import reverse
from django.utils import timezone

from admissions.models import Attendee
from tests.test_registration_gedik_student import register


@pytest.fixture
def staff(client, organizer, settings):
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    session = client.session
    session["mfa_at"] = timezone.now().timestamp()
    session.save()
    return client


def cells(client, event, key):
    html = client.get(reverse("resource-list", args=[event.slug, key])).content.decode()
    row = re.search(r"<tbody>(.*?)</tr>", html, re.S).group(1)
    return {
        label: " ".join(re.sub(r"<[^>]+>", " ", body).split())
        for label, body in re.findall(r'<td[^>]*data-label="([^"]+)"[^>]*>(.*?)</td>', row, re.S)
    }


@pytest.mark.django_db
def test_attendee_table_columns_match_headings(client, event, staff):
    register(client, event, arrives_by_car="yes", vehicle_plate="34 ABC 123")
    attendee = Attendee.objects.get()
    row = cells(staff, event, "attendees")
    assert row["Attendee"] == f"{attendee.name} {attendee.email} · {attendee.phone}"
    assert row["Registration status"] == attendee.registration.get_status_display()
    assert row["Ticket status"] == f"{attendee.ticket.get_status_display()} QR status: Active"
    assert row["Attendance"] == "Not admitted"


@pytest.mark.django_db
def test_ticket_table_columns_match_headings(client, event, staff):
    register(client, event)
    ticket = Attendee.objects.get().ticket
    row = cells(staff, event, "tickets")
    assert row["Attendee"] == f"{ticket.attendee.name} {ticket.reference}"
    assert row["Ticket type"] == ticket.ticket_type.name
    assert row["Ticket status"] == f"{ticket.get_status_display()} QR status: Active"
    assert row["Attendance"] == "Not admitted"
