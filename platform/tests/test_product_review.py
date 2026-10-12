"""Visual product walkthrough with synthetic records, separate from the real event."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright
from admissions.models import Attendee, Registration
from admissions.services import new_action_token
from program.models import Speaker, ScheduleItem
from core.resources import RESOURCES
from core.models import RateBucket
from tests.test_admission import allocate
from tests.test_browser import accessibility, database


@pytest.mark.django_db(transaction=True)
def test_product_visual_walkthrough(live_server, event, organizer, settings):
    settings.MFA_REQUIRED = False
    settings.DEBUG = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    settings.PUBLIC_BASE_URL = live_server.url
    event.name = "TEDxGedik University"
    event.enabled_languages = ["en", "tr", "ar"]
    event.capacity = 100
    event.venue = "University auditorium · Campus entrance"
    event.venue_confirmed = True
    event.map_url = "https://www.google.com/maps/search/?api=1&query=Istanbul+Gedik+University"
    event.volunteer_open = True
    event.contact_email = "team@example.invalid"
    event.save()
    for index, name in enumerate(["Deniz Kaya", "ليلى أحمد", "Alex Morgan", "Elif Demir", "Omar Yilmaz"]):
        attendee = Attendee.objects.create(
            event=event, name=name, email=f"guest-{index}@example.invalid", notice_version="test-1"
        )
        Registration.objects.create(event=event, attendee=attendee, status="under_review")
    ticket, credential = allocate(event, organizer, "ticket@example.invalid")
    token = new_action_token(ticket.attendee)
    speakers = []
    for name, bio in [
        ("Deniz Kaya", "Exploring the connection between design, everyday life and the places we share."),
        ("ليلى أحمد", "أفكار جديدة حول التعليم والمعرفة والمستقبل الذي نبنيه معًا."),
        ("Alex Morgan", "A researcher asking how small changes can create a lasting impact."),
    ]:
        speakers.append(
            Speaker.objects.create(
                event=event, name=name, biography=bio, published_snapshot={"name": name, "biography": bio}
            )
        )
    for index, title in enumerate(
        ["Welcome & opening", "From Ideas to Impact", "A different perspective"]
    ):
        start = event.starts_at + timedelta(minutes=index * 30)
        ScheduleItem.objects.create(
            event=event,
            title=title,
            kind="opening",
            starts_at=start,
            ends_at=start + timedelta(minutes=20),
            published_snapshot={
                "title": title,
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(minutes=20)).isoformat(),
                "description": "A shared space for thoughtful conversations.",
            },
        )
    phase = os.environ.get("TEDX_VISUAL_PHASE", "final")
    output = Path(settings.ROOT_DIR) / ".local/deep-ux" / phase
    output.mkdir(parents=True, exist_ok=True)
    routes = [
        ("home", "/"),
        ("login", reverse("login")),
        ("recover-account", reverse("password-recover")),
        ("register", reverse("register", args=[event.slug])),
        ("volunteer", reverse("volunteer-apply", args=[event.slug])),
        ("ticket", reverse("ticket-access", args=[event.slug, token])),
    ]
    routes += [
        (key, reverse("public-page", args=[event.slug, key]))
        for key in ["about", "speakers", "program", "venue", "faq", "contact", "privacy", "terms", "theme"]
    ]
    routes += [
        ("speaker", reverse("speaker", args=[event.slug, speakers[0].pk])),
        ("recover-ticket", reverse("recover", args=[event.slug])),
        ("recover-volunteer", reverse("volunteer-recover", args=[event.slug])),
    ]
    routes += [
        ("dashboard", reverse("dashboard", args=[event.slug])),
        ("scanner", reverse("scanner", args=[event.slug])),
        ("event-settings", reverse("event-settings", args=[event.slug])),
        ("reports", reverse("reports", args=[event.slug])),
        ("mfa", reverse("mfa")),
        ("password", reverse("password_change")),
    ]
    routes += [
        (f"group-{key}", reverse("workspace-group", args=[event.slug, key]))
        for key in ["people", "event", "team", "settings"]
    ]
    routes += [(f"list-{key}", reverse("resource-list", args=[event.slug, key])) for key in RESOURCES]
    routes += [
        (f"form-{key}", reverse("resource-create", args=[event.slug, key]))
        for key, r in RESOURCES.items()
        if r.fields and key not in {"attendees", "registrations"}
    ]
    routes += [
        ("speaker-detail", reverse("resource-detail", args=[event.slug, "speakers", speakers[0].pk])),
        ("speaker-photo", reverse("speaker-photo", args=[event.slug, speakers[0].pk])),
        ("ticket-detail", reverse("resource-detail", args=[event.slug, "tickets", ticket.pk])),
    ]
    routes += [
        (
            "speaker-publish",
            reverse("resource-action", args=[event.slug, "speakers", speakers[0].pk, "publish"]),
        ),
        ("users", reverse("users", args=[event.slug])),
        ("invite", reverse("invite-user", args=[event.slug])),
        ("imports", reverse("imports", args=[event.slug])),
        ("roster", reverse("roster", args=[event.slug])),
    ]
    matrix = (
        [("en", 1440), ("ar", 390)]
        if phase in {"before", "review"}
        else [(lang, width) for lang in ["en", "tr", "ar"] for width in [1440, 1280, 1024, 390, 360]]
    )
    selected_routes = os.environ.get("TEDX_VISUAL_ROUTES", "").split(",")
    if selected_routes != [""]:
        routes = [(name, route) for name, route in routes if name in selected_routes]
    records, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server.url + reverse("login"))
        page.get_by_label("Username").fill(organizer.username)
        page.get_by_label("Password:", exact=True).fill("Long-test-only-password-62")
        page.get_by_role("button", name="Sign in", exact=True).click()
        # Traverse every visible local navigation link, preserving its real destination.
        followed = set()
        for source in [
            reverse("dashboard", args=[event.slug]),
            *[
                reverse("workspace-group", args=[event.slug, key])
                for key in ["people", "event", "team", "settings"]
            ],
        ]:
            page.goto(live_server.url + source)
            links = page.locator("main a[href], .sidebar a[href]").evaluate_all(
                '(es)=>es.map(e=>e.getAttribute("href"))'
            )
            for href in dict.fromkeys(links):
                if not href or not href.startswith("/") or href in followed:
                    continue
                page.goto(live_server.url + source)
                link = page.locator('a[href="' + href + '"]').filter(visible=True)
                if link.count():
                    link.first.click()
                    assert urlsplit(page.url).path == urlsplit(href).path
                    followed.add(href)
        for language, width in matrix:
            page.context.add_cookies([{"name": "django_language", "value": language, "url": live_server.url}])
            page.set_viewport_size({"width": width, "height": 960})
            for name, route in routes:
                response = page.goto(live_server.url + route)
                assert response.status == 200, (name, response.status)
                page.evaluate("document.fonts.ready")
                overflow = page.evaluate("document.documentElement.scrollWidth>innerWidth")
                filename = f"{language}-{width}-{name}.png"
                page.screenshot(path=str(output / filename), full_page=True)
                records.append(
                    {
                        "name": name,
                        "language": language,
                        "width": width,
                        "file": filename,
                        "overflow": overflow,
                    }
                )
                if phase != "before":
                    assert not overflow, (name, language, width)
                    if width in [390, 1440] and name in [
                        "home",
                        "about",
                        "register",
                        "ticket",
                        "dashboard",
                        "scanner",
                        "list-attendees",
                        "list-tickets",
                        "form-speakers",
                        "speaker-photo",
                        "event-settings",
                        "login",
                    ]:
                        accessibility(page)
            # Interaction states supplement the route atlas; mutations remain in the test DB.
            page.goto(live_server.url + reverse("ticket-access", args=[event.slug, token]))
            page.locator(".ticket-controls summary").first.click()
            page.locator("form[data-confirm] button").first.click()
            page.screenshot(path=str(output / f"{language}-{width}-confirmation.png"), full_page=True)
            page.keyboard.press("Escape")
            assert not page.locator("#confirmation").is_visible()
            page.locator(".language-menu summary").click()
            page.screenshot(path=str(output / f"{language}-{width}-language-menu.png"), full_page=True)
            database(
                lambda: (
                    type(event)
                    .objects.filter(pk=event.pk)
                    .update(opens_at=timezone.now() + timedelta(days=1))
                )
            )
            page.goto(live_server.url + reverse("register", args=[event.slug]))
            page.screenshot(path=str(output / f"{language}-{width}-registration-closed.png"), full_page=True)
            assert page.locator('input[name="email"]').count() == 0
            database(lambda: type(event).objects.filter(pk=event.pk).update(opens_at=event.opens_at))
            # Each viewport represents a separate journey; reset test-only rate buckets.
            database(lambda: RateBucket.objects.all().delete())
            # Recovery uses the existing generic success screen without exposing account existence.
            page.goto(live_server.url + reverse("recover", args=[event.slug]))
            page.locator('input[name="email"]').fill("state-review@example.invalid")
            page.locator(".form-stack button[type=submit]").click()
            assert page.locator(".success-mark").is_visible()
            page.screenshot(path=str(output / f"{language}-{width}-success.png"), full_page=True)
            # Camera permission is denied in the headless browser; recovery controls must remain visible.
            page.goto(live_server.url + reverse("scanner", args=[event.slug]))
            page.locator("#start-camera").click()
            page.locator("#scan-result.failure").wait_for(state="visible")
            page.screenshot(path=str(output / f"{language}-{width}-camera-unavailable.png"), full_page=True)
            settings.DEBUG = False
            response = page.goto(live_server.url + "/missing-review-page/")
            assert response.status == 404
            page.screenshot(path=str(output / f"{language}-{width}-not-found.png"), full_page=True)
            settings.DEBUG = True
            # Actual empty search and server validation.

            page.goto(
                live_server.url + reverse("resource-list", args=[event.slug, "attendees"]) + "?q=not-a-person"
            )
            page.screenshot(path=str(output / f"{language}-{width}-no-results.png"), full_page=True)
            page.goto(live_server.url + reverse("resource-create", args=[event.slug, "speakers"]))
            page.locator("form.form-stack").evaluate("(f)=>f.noValidate=true")
            page.locator("form.form-stack button[type=submit]").click()
            page.screenshot(path=str(output / f"{language}-{width}-form-errors.png"), full_page=True)
        # An explicit confirmation is inspected and dismissed; the ticket remains unchanged.
        page.context.add_cookies([{"name": "django_language", "value": "en", "url": live_server.url}])
        page.goto(live_server.url + reverse("ticket-access", args=[event.slug, token]))
        page.get_by_text("Manage ticket", exact=True).click()
        page.get_by_role("button", name="Cancel ticket", exact=True).click()
        page.locator("#confirmation-cancel").click()
        # Verify the language form itself, including RTL switching and preserved destination.
        page.locator(".language-menu summary").click()
        page.locator('.language-switch button[value="ar"]').click()
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert urlsplit(page.url).path == reverse("ticket-access", args=[event.slug, token])
        browser.close()
    (output / "inventory.json").write_text(
        json.dumps(
            {"screens": records, "followed_links": sorted(followed), "errors": errors},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    assert not errors