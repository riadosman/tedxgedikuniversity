"""Development shortcut stays local, explicit, CSRF-protected and separate from real staff."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from core.auth_views import recent_mfa
from core.dev_access import DEV_USERNAME
from core.models import AuditLog, RoleGrant


@pytest.fixture(autouse=True)
def dev_settings(settings):
    settings.PRODUCTION = False
    settings.DEBUG = True
    settings.DEV_ONE_CLICK_LOGIN = True
    settings.DEV_LOGIN_EVENT = "test"
    settings.MFA_REQUIRED = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver", "public.example"]


@pytest.mark.django_db
def test_one_click_login_with_csrf_and_existing_rbac(event, organizer):
    client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
    url = reverse("development-login")
    assert client.get(url).status_code == 405
    assert client.post(url).status_code == 403
    page = client.get(reverse("login"))
    assert "Geliştirme için tek tıkla giriş" in page.content.decode()
    csrf = client.cookies["csrftoken"].value
    response = client.post(url, {"csrfmiddlewaretoken": csrf, "next": "https://untrusted.example"})
    assert response.status_code == 302
    assert response.url == reverse("dashboard", args=[event.slug])
    assert client.get(response.url).status_code == 200
    user = get_user_model().objects.get(username=DEV_USERNAME)
    assert not user.has_usable_password() and not user.is_superuser
    assert RoleGrant.objects.filter(user=user, event=event, role="organizer", active=True).exists()
    assert AuditLog.objects.filter(actor=user, action="auth.development_login").exists()
    assert organizer.check_password("Long-test-only-password-62")
    request = RequestFactory().get("/", HTTP_HOST="localhost")
    request.user, request.session = user, client.session
    recent_mfa(request)
    csrf = client.cookies["csrftoken"].value
    assert client.post(url, {"csrfmiddlewaretoken": csrf}).status_code == 302
    assert get_user_model().objects.filter(username=DEV_USERNAME).count() == 1
    assert RoleGrant.objects.filter(user=user).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["production", "disabled", "no_debug", "remote", "public_host", "proxy"])
def test_shortcut_unavailable_outside_explicit_local_environment(event, settings, change):
    options = {"HTTP_HOST": "localhost"}
    if change == "production":
        settings.PRODUCTION = True
    elif change == "disabled":
        settings.DEV_ONE_CLICK_LOGIN = False
    elif change == "no_debug":
        settings.DEBUG = False
    elif change == "remote":
        options["REMOTE_ADDR"] = "192.168.1.5"
    elif change == "public_host":
        options["HTTP_HOST"] = "public.example"
    else:
        options["HTTP_X_FORWARDED_FOR"] = "127.0.0.1"
    client = Client(**options)
    assert b"development-login-title" not in client.get(reverse("login")).content
    assert client.post(reverse("development-login")).status_code == 404
    assert not get_user_model().objects.filter(username=DEV_USERNAME).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["production", "disabled", "remote"])
def test_existing_development_session_is_revoked(event, settings, change):
    client = Client(HTTP_HOST="localhost")
    assert client.post(reverse("development-login")).status_code == 302
    options = {}
    if change == "production":
        settings.PRODUCTION = True
    elif change == "disabled":
        settings.DEV_ONE_CLICK_LOGIN = False
    else:
        options["REMOTE_ADDR"] = "192.168.1.5"
    response = client.get(reverse("dashboard", args=[event.slug]), **options)
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_ordinary_staff_still_requires_mfa(client, event, organizer):
    client.force_login(organizer)
    response = client.get(reverse("dashboard", args=[event.slug]), HTTP_HOST="localhost")
    assert response.status_code == 302 and response.url == reverse("mfa")


@pytest.mark.django_db
def test_reserved_username_does_not_take_over_existing_account(event):
    user = get_user_model().objects.create_user(DEV_USERNAME, password="Existing-secret-62")
    client = Client(HTTP_HOST="localhost")
    assert client.post(reverse("development-login")).status_code == 403
    user.refresh_from_db()
    assert user.check_password("Existing-secret-62")
    assert not RoleGrant.objects.filter(user=user).exists()
