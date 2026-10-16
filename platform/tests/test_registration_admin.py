"""Staff edit and delete registrations; issued tickets follow a moved event date."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from admissions.models import ActionToken, Credential, Ticket
from admissions.services import check_in, committed, new_action_token, submit_registration, notice_digest
from core.forms import EventForm
from core.models import AuditLog, RoleGrant


def registered(event, email="guest@example.invalid"):
    return submit_registration(
        event,
        name="Test Guest",
        email=email,
        phone="+90 532 123 45 67",
        arrives_by_car=False,
        privacy_acknowledged=True,
        notice_version=event.notice_version,
        notice_hash=notice_digest(event),
    ).attendee


@pytest.fixture
def staff(client, organizer, settings):
    settings.MFA_REQUIRED = False
    client.force_login(organizer)
    return client


def edit(client, attendee, **changes):
    return client.post(
        reverse("resource-edit", args=[attendee.event.slug, "attendees", attendee.pk]),
        {
            "name": attendee.name,
            "email": attendee.email,
            "phone": attendee.phone,
            "arrives_by_car": "false",
            "vehicle_plate": "",
            "version": attendee.version,
            "correction_reason": "Attendee asked by phone",
            **changes,
        },
    )


def delete(client, attendee, reason="Duplicate registration"):
    return client.post(
        reverse("resource-action", args=[attendee.event.slug, "attendees", attendee.pk, "delete"]),
        {"reason": reason},
    )


@pytest.mark.django_db
def test_staff_edit_phone_car_and_plate(staff, event):
    attendee = registered(event)
    response = edit(staff, attendee, phone="0532 111 22 33", arrives_by_car="true", vehicle_plate="06abc12")
    assert response.status_code == 302
    attendee.refresh_from_db()
    assert (attendee.phone, attendee.arrives_by_car, attendee.vehicle_plate) == (
        "0532 111 22 33",
        True,
        "06 ABC 12",
    )
    assert AuditLog.objects.filter(action="attendee.corrected", target=str(attendee.pk)).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("bad", [{"arrives_by_car": "true", "vehicle_plate": ""}, {"phone": "12345"}])
def test_staff_edit_validates_like_registration(staff, event, bad):
    attendee = registered(event)
    response = edit(staff, attendee, **bad)
    assert response.status_code == 200
    attendee.refresh_from_db()
    assert (attendee.phone, attendee.arrives_by_car) == ("+90 532 123 45 67", False)


@pytest.mark.django_db
def test_staff_edit_clears_plate_when_not_by_car(staff, event):
    attendee = registered(event)
    edit(staff, attendee, arrives_by_car="true", vehicle_plate="34 ABC 123")
    attendee.refresh_from_db()
    edit(staff, attendee, arrives_by_car="false", vehicle_plate="34 ABC 123")
    attendee.refresh_from_db()
    assert (attendee.arrives_by_car, attendee.vehicle_plate) == (False, "")


@pytest.mark.django_db
def test_delete_asks_for_confirmation(staff, event):
    attendee = registered(event)
    detail = staff.get(
        reverse("resource-detail", args=[event.slug, "attendees", attendee.pk])
    ).content.decode()
    action = reverse("resource-action", args=[event.slug, "attendees", attendee.pk, "delete"])
    assert f'href="{action}"' in detail
    page = staff.get(action).content.decode()
    assert "data-confirm=" in page
    assert "Delete this registration?" in page


@pytest.mark.django_db
def test_delete_cancels_ticket_frees_seat_and_erases_personal_data(staff, event):
    attendee = registered(event)
    ticket = Ticket.objects.get(attendee=attendee)
    response = delete(staff, attendee)
    assert response.status_code == 302
    assert response.url == reverse("resource-list", args=[event.slug, "attendees"])
    ticket.refresh_from_db()
    attendee.refresh_from_db()
    assert ticket.status == "cancelled" and committed(event) == 0
    assert not Credential.objects.filter(ticket=ticket, revoked_at__isnull=True).exists()
    assert not ActionToken.objects.filter(attendee=attendee).exists()
    assert attendee.anonymized_at is not None
    assert (attendee.email, attendee.phone, attendee.vehicle_plate) == (None, "", "")
    assert "Test Guest" != attendee.name
    assert AuditLog.objects.filter(action="registration.deleted", target=str(attendee.pk)).exists()


@pytest.mark.django_db
def test_deleted_registration_leaves_list_and_email_can_register_again(staff, event):
    delete(staff, registered(event))
    listing = staff.get(reverse("resource-list", args=[event.slug, "attendees"])).content.decode()
    assert "Anonymized attendee" not in listing
    assert registered(event).email == "guest@example.invalid"


@pytest.mark.django_db
def test_delete_needs_a_reason(staff, event):
    attendee = registered(event)
    assert delete(staff, attendee, reason=" ").status_code == 200
    attendee.refresh_from_db()
    assert attendee.anonymized_at is None


@pytest.mark.django_db
def test_admitted_attendee_cannot_be_deleted(staff, event, organizer):
    attendee = registered(event)
    event.entry_mode = "online"
    event.save()
    credential = Credential.objects.get(ticket__attendee=attendee)
    from cryptography.fernet import Fernet
    from django.conf import settings

    raw = Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(credential.ciphertext.encode()).decode()
    check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)
    assert delete(staff, attendee).status_code == 200
    attendee.refresh_from_db()
    assert attendee.anonymized_at is None and attendee.name == "Test Guest"


@pytest.mark.django_db
def test_delete_requires_attendee_edit_permission(client, event, settings):
    settings.MFA_REQUIRED = False
    attendee = registered(event)
    user = get_user_model().objects.create_user("door", password="Long-test-only-password-62")
    RoleGrant.objects.create(event=event, user=user, role="checkin", reason="Test fixture")
    client.force_login(user)
    assert delete(client, attendee).status_code == 403
    attendee.refresh_from_db()
    assert attendee.anonymized_at is None


def settings_form_data(event, **changes):
    form = EventForm(instance=event)
    data = {"version": event.version}
    for name in form.fields:
        value = form[name].value()
        if isinstance(value, bool):
            if value:
                data[name] = "on"
        elif hasattr(value, "tzinfo"):  # The form already converted it to naive event time.
            data[name] = value.strftime("%Y-%m-%dT%H:%M")
        elif value is not None:
            data[name] = value
    for name, value in changes.items():
        data[name] = timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")
    return data


@pytest.mark.django_db
def test_moving_the_event_date_keeps_issued_tickets_and_links_valid(staff, event):
    attendee = registered(event)
    token = new_action_token(attendee)
    new_start, new_end = event.starts_at + timedelta(days=31), event.ends_at + timedelta(days=31)
    response = staff.post(
        reverse("event-settings", args=[event.slug]),
        settings_form_data(event, starts_at=new_start, ends_at=new_end),
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    event.refresh_from_db()
    assert event.ends_at.date() == new_end.date()
    assert Ticket.objects.get(attendee=attendee).expires_at == event.ends_at
    access = ActionToken.objects.filter(attendee=attendee, purpose="manage").latest("created_at")
    assert access.expires_at == event.ends_at + timedelta(days=1)
    assert staff.get(reverse("ticket-access", args=[event.slug, token])).status_code == 200


@pytest.mark.django_db
def test_registration_record_offers_edit_and_delete(staff, event):
    attendee = registered(event)
    registration = attendee.registration
    page = staff.get(
        reverse("resource-detail", args=[event.slug, "registrations", registration.pk])
    ).content.decode()
    assert f'href="{reverse("resource-edit", args=[event.slug, "attendees", attendee.pk])}"' in page
    assert (
        f'href="{reverse("resource-action", args=[event.slug, "registrations", registration.pk, "delete"])}"'
        in page
    )


@pytest.mark.django_db
def test_delete_from_registrations_list(staff, event):
    attendee = registered(event)
    response = staff.post(
        reverse("resource-action", args=[event.slug, "registrations", attendee.registration.pk, "delete"]),
        {"reason": "Duplicate registration"},
    )
    assert response.url == reverse("resource-list", args=[event.slug, "registrations"])
    attendee.refresh_from_db()
    assert attendee.anonymized_at is not None
    listing = staff.get(response.url).content.decode()
    assert str(attendee.registration.pk) not in listing


@pytest.mark.django_db
def test_overview_counts_follow_a_deleted_registration(staff, event):
    def overview():
        stats = staff.get(reverse("dashboard", args=[event.slug])).context["stats"]
        return {str(label): value for label, value in stats}

    registered(event)
    gone = registered(event, email="second@example.invalid")
    before = overview()
    assert before["Registrations"] == 2 and before["Valid tickets"] == 2
    delete(staff, gone)
    after = overview()
    assert after["Registrations"] == 1
    assert after["Valid tickets"] == 1 and after["Cancelled tickets"] == 1
