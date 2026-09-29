import uuid

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from admissions.services import check_in, ensure_intake, set_entry_mode, submit_registration
from core.forms import RegistrationForm
from tests.test_admission import allocate


@pytest.mark.django_db
def test_unpublished_notice_is_not_claimed_as_accepted(event, client):
    event.privacy_approved = False
    event.privacy_notice = "Private unfinished draft"
    event.save()
    response = client.get(reverse("register", args=[event.slug]))
    assert response.status_code == 200
    assert b"Private unfinished draft" not in response.content
    assert b'id_privacy"' not in response.content
    assert "privacy" in RegistrationForm(event).fields
    with pytest.raises(ValidationError, match="approved KVKK"):
        submit_registration(event, name="Applicant", email="draft@example.invalid")



@pytest.mark.django_db
def test_approved_notice_still_requires_acknowledgement_and_policy(event):
    form = RegistrationForm(event, {"name": "Applicant", "email": "test@example.invalid"})
    assert not form.is_valid()
    assert "privacy" in form.errors
    event.policy_approved = False
    with pytest.raises(ValidationError):
        ensure_intake(event)
    with pytest.raises(ValidationError):
        event.full_clean()


@pytest.mark.django_db
def test_ticket_admission_without_publishing_privacy_draft(event, organizer):
    _, credential = allocate(event, organizer)
    event.privacy_approved = False
    event.save()
    set_entry_mode(event, organizer, "online", "Ready to receive attendees")
    result = check_in(event, organizer, request_id=uuid.uuid4(), credential=credential)
    assert result["code"] == "VALID"
    repeated = check_in(event, organizer, request_id=uuid.uuid4(), credential=credential)
    assert repeated["code"] == "ALREADY_CHECKED_IN"
