import pytest
from django.forms.models import model_to_dict
from core.forms import EventForm


@pytest.mark.django_db
def test_volunteer_settings_identifies_each_missing_privacy_field(event):
    data = model_to_dict(event)
    data.update(
        volunteer_open=True,
        privacy_notice="",
        notice_version="",
        privacy_approved=False,
        registration_mode="closed",
    )
    form = EventForm(data=data, instance=event)
    assert not form.is_valid()
    assert {"privacy_notice", "notice_version", "privacy_approved"} <= set(form.errors)
    steps = {name: complete for name, _, _, complete in form.volunteer_steps()}
    assert not steps["privacy_notice"]
    assert not steps["notice_version"]
    assert not steps["privacy_approved"]
    event.refresh_from_db()
    assert not event.volunteer_open
    assert event.privacy_notice == "Test notice"
