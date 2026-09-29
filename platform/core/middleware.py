import time
import logging
import uuid
import json
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from .dev_access import DEV_USERNAME, DEV_SESSION_KEY, development_session, loopback_request
from django.http import HttpResponseNotFound


class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.local_event_rehearsal = bool(
            settings.DEV_EVENT_REHEARSAL and settings.DEBUG and not settings.PRODUCTION
        )
        if settings.DEV_EVENT_REHEARSAL and (
            settings.PRODUCTION or not settings.DEBUG or not loopback_request(request)
        ):
            return HttpResponseNotFound()
        started = time.monotonic()
        request_id = str(uuid.uuid4())
        if request.user.is_authenticated:
            local_session = development_session(request)
            if (
                request.user.username == DEV_USERNAME or request.session.get(DEV_SESSION_KEY)
            ) and not local_session:
                logout(request)
                return redirect(settings.LOGIN_URL)
            session_start = request.session.setdefault("session_started", time.time())
            last = request.session.get("last_activity", time.time())
            if time.time() - last > 1800 or time.time() - session_start > 8 * 3600:
                logout(request)
                return redirect(settings.LOGIN_URL)
            request.session["last_activity"] = time.time()
            if (
                request.path.startswith(("/staff/", "/accounts/password/"))
                and settings.MFA_REQUIRED
                and not request.user.is_verified()
                and not local_session
            ):
                return redirect("mfa")
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        if (
            request.path.startswith(("/staff/", "/accounts/"))
            or "/access/" in request.path
            or "/volunteer-access/" in request.path
        ):
            response["Cache-Control"] = "no-store, private"
            response["Referrer-Policy"] = "strict-origin"
            response["X-Robots-Tag"] = "noindex, nofollow"
        logging.getLogger("event.requests").info(
            json.dumps(
                {
                    "request_id": request_id,
                    "route": getattr(request.resolver_match, "url_name", None) or "unmatched",
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "actor_id": request.user.pk if request.user.is_authenticated else None,
                }
            )
        )
        return response
