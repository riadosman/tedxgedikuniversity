"""Explicit shareable language links, using Django's existing locale cookie."""

from collections.abc import Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation


class LanguageLinkMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = request.GET.get("lang")
        if language not in dict(settings.LANGUAGES):
            return self.get_response(request)
        assert language is not None
        with translation.override(language):
            request.LANGUAGE_CODE = language
            response = self.get_response(request)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
        response["Content-Language"] = language
        return response
