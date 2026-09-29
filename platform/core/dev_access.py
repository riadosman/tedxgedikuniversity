"""Explicit local-only development access using the existing user/session/RBAC stack."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from django.conf import settings
from .models import Event

DEV_USERNAME = "_tedx_local_developer"
DEV_SESSION_KEY = "local_development_user"


def local_development_access_allowed(request):
    if settings.PRODUCTION or not settings.DEBUG or not settings.DEV_ONE_CLICK_LOGIN:
        return False
    return loopback_request(request)


def loopback_request(request):
    if any(
        key in request.META
        for key in (
            "HTTP_FORWARDED",
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_FORWARDED_HOST",
            "HTTP_X_FORWARDED_PROTO",
        )
    ):
        return False
    try:
        address = ip_address(request.META.get("REMOTE_ADDR", ""))
        host = urlsplit("//" + request.get_host()).hostname
    except ValueError:
        return False
    return address.is_loopback and host in {"127.0.0.1", "localhost", "::1"}


def event_rehearsal(event: Event) -> bool:
    return bool(
        settings.DEBUG
        and not settings.PRODUCTION
        and settings.DEV_EVENT_REHEARSAL
        and event.slug == settings.DEV_LOGIN_EVENT
    )


def development_session(request):
    return (
        local_development_access_allowed(request)
        and request.user.is_authenticated
        and request.user.username == DEV_USERNAME
        and request.session.get(DEV_SESSION_KEY) == request.user.pk
    )
