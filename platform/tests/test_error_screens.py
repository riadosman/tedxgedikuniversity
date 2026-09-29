"""Error boundaries use translated recovery screens without leaking exception details."""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import override
from django.views.defaults import server_error


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "tr", "ar"])
def test_error_recovery_screens(event, client, settings, language):
    settings.DEBUG = False
    settings.MFA_REQUIRED = False
    client.cookies["django_language"] = language
    missing = client.get("/missing-review-page/")
    assert missing.status_code == 404
    assert "error-page" in missing.content.decode()
    outsider = get_user_model().objects.create_user("outside-review")
    client.force_login(outsider)
    forbidden = client.get(reverse("dashboard", args=[event.slug]))
    assert forbidden.status_code == 403
    assert "error-page" in forbidden.content.decode()
    with override(language):
        failure = server_error(RequestFactory().get("/"))
    assert failure.status_code == 500
    for response in [missing, forbidden, failure]:
        markup = response.content.decode()
        assert "Traceback" not in markup
        assert 'href="/"' in markup
        assert f'lang="{language}"' in markup
        assert 'dir="rtl"' in markup if language == "ar" else 'dir="ltr"' in markup
