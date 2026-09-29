"""Responsive regression coverage using isolated real application records."""

from pathlib import Path
import pytest
from django.urls import reverse
from playwright.sync_api import sync_playwright, expect
from tests.test_browser import database, accessibility
from tests.test_admission import allocate
from admissions.services import new_action_token
from program.models import Speaker, ScheduleItem
from core.resources import RESOURCES


@pytest.mark.django_db(transaction=True)
def test_design_responsive_matrix(live_server, event, organizer, settings):
    settings.MFA_REQUIRED = False
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    settings.DEBUG = True
    event.enabled_languages = ["en", "tr", "ar"]
    event.save()
    ticket, _ = allocate(event, organizer)
    token = new_action_token(ticket.attendee)
    speaker = Speaker.objects.create(
        event=event,
        name="Rehearsal speaker",
        published_snapshot={"name": "Rehearsal speaker", "biography": "Synthetic browser test biography."},
    )
    ScheduleItem.objects.create(
        event=event,
        title="Rehearsal talk",
        kind="talk",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        published_snapshot={
            "title": "Rehearsal talk",
            "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat(),
            "description": "Synthetic test session.",
        },
    )
    artifacts = Path(settings.ROOT_DIR) / ".local/test-artifacts/design"
    artifacts.mkdir(parents=True, exist_ok=True)
    public_routes = [
        "/",
        reverse("register", args=[event.slug]),
        reverse("volunteer-apply", args=[event.slug]),
        reverse("speaker", args=[event.slug, speaker.pk]),
        reverse("public-page", args=[event.slug, "program"]),
        reverse("ticket-access", args=[event.slug, token]),
    ]
    staff_routes = [
        reverse("event-settings", args=[event.slug]),
        reverse("resource-create", args=[event.slug, "speakers"]),
        reverse("dashboard", args=[event.slug]),
        reverse("scanner", args=[event.slug]),
        reverse("resource-list", args=[event.slug, "tickets"]),
        reverse("resource-detail", args=[event.slug, "speakers", speaker.pk]),
        reverse("resource-create", args=[event.slug, "incidents"]),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server.url + "/accounts/login/")
        page.get_by_label("Username").fill(organizer.username)
        page.get_by_label("Password:", exact=True).fill("Long-test-only-password-62")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("heading", name="Event-day dashboard")).to_be_visible()
        for width in [768, 320, 375, 390, 430, 1024, 1440, 1920]:
            page.set_viewport_size({"width": width, "height": 900})
            for index, route in enumerate(public_routes + staff_routes):
                response = page.goto(live_server.url + route)
                assert response.status == 200, route
                if not page.evaluate("document.documentElement.scrollWidth <= innerWidth"):
                    page.screenshot(path=str(artifacts / "overflow.png"), full_page=True)
                    overflow = page.evaluate(
                        """Array.from(document.querySelectorAll('*')).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right,scroll:e.scrollWidth})).filter(e=>e.right>innerWidth).slice(0,25)"""
                    )
                    pytest.fail(str((width, route, overflow)))
                if width in [320, 1440]:
                    accessibility(page)
                    page.screenshot(path=str(artifacts / f"{width}-{index}.png"), full_page=True)
            if width == 320:
                page.goto(live_server.url)
                menu = page.locator("#public-menu")
                menu.click()
                expect(menu).to_have_attribute("aria-expanded", "true")
                page.keyboard.press("Escape")
                expect(menu).to_be_focused()
                expect(page.locator("#public-navigation")).not_to_be_visible()
                page.goto(live_server.url + public_routes[-1])
                page.get_by_text("Manage ticket", exact=True).click()
                page.get_by_role("button", name="Cancel ticket", exact=True).click()
                page.locator("#confirmation-cancel").click()
                expect(page.get_by_role("button", name="Cancel ticket", exact=True)).to_be_enabled()
                assert database(lambda: type(ticket).objects.get(pk=ticket.pk).status) == "registered"
        # Every permission-visible resource uses the same tested list and form system.
        page.set_viewport_size({"width": 390, "height": 844})
        for key in RESOURCES:
            response = page.goto(live_server.url + reverse("resource-list", args=[event.slug, key]))
            assert response.status == 200, (key, response.status)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), key
        extra_routes = [
            reverse("public-page", args=[event.slug, key])
            for key in ["about", "theme", "speakers", "venue", "faq", "contact", "privacy", "terms"]
        ]
        extra_routes += [
            reverse("recover", args=[event.slug]),
            reverse("volunteer-recover", args=[event.slug]),
            reverse("speaker-photo", args=[event.slug, speaker.pk]),
        ]
        extra_routes += [
            reverse("workspace-group", args=[event.slug, key])
            for key in ["people", "event", "team", "settings"]
        ]
        for language, direction in [("en", "ltr"), ("tr", "ltr"), ("ar", "rtl")]:
            page.context.add_cookies([{"name": "django_language", "value": language, "url": live_server.url}])
            for width in [390, 1440]:
                page.set_viewport_size({"width": width, "height": 900})
                for index, route in enumerate(public_routes + staff_routes + extra_routes):
                    response = page.goto(live_server.url + route)
                    assert response.status == 200, (language, route)
                    expect(page.locator("html")).to_have_attribute("dir", direction)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        language,
                        route,
                    )
                    if index in [0, 1, 5, 8, 9] or route in extra_routes:
                        accessibility(page)
                    if index in [0, 1, 5, 8, 9]:
                        page.screenshot(
                            path=str(artifacts / f"{language}-{width}-{index}.png"), full_page=True
                        )
            page.set_viewport_size({"width": 390, "height": 844})
            for key, resource in RESOURCES.items():
                if resource.fields and key not in {"attendees", "registrations", "invitations"}:
                    response = page.goto(live_server.url + reverse("resource-create", args=[event.slug, key]))
                    assert response.status == 200, (language, key)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        language,
                        key,
                    )
            page.goto(live_server.url + reverse("dashboard", args=[event.slug]))
            page.locator("#mobile-menu").click()
            expect(page.locator("#workspace-navigation")).to_be_visible()
            assert page.locator(".sidebar nav > a").count() <= 7
            page.keyboard.press("Escape")
            expect(page.locator("#mobile-menu")).to_be_focused()
        page.goto(live_server.url + reverse("event-settings", args=[event.slug]) + "?lang=tr")
        expect(page.get_by_role("heading", name="Etkinlik ve kayıt ayarları")).to_be_visible()
        # The retired custom attendee-question section is no longer part of settings.
        expect(page.locator("fieldset")).to_have_count(5)
        page.locator(".setup-guide summary").click()
        page.get_by_role("link", name="Gizlilik metnine git", exact=True).click()
        expect(page.locator("#id_privacy_notice")).to_be_focused()
        page.locator("#id_privacy_notice").fill("")
        expect(page.locator('[data-setup-field="id_privacy_notice"] .setup-state')).to_have_text(
            "Tamamlanacak"
        )
        page.locator("#id_privacy_notice").fill("Synthetic approved test notice")
        expect(page.locator('[data-setup-field="id_privacy_notice"] .setup-state')).to_have_text("Dolduruldu")

        expect(page.get_by_label("Kayıt modu", exact=False)).to_have_count(1)
        assert page.locator("#id_payment_mode option[value=free]").text_content() == "Ücretsiz"
        expect(page.locator("#id_opens_at")).to_have_attribute("type", "datetime-local")
        page.goto(live_server.url + reverse("resource-create", args=[event.slug, "speakers"]) + "?lang=tr")
        expect(page.get_by_label("Fotoğraf", exact=False)).to_have_count(1)
        page.locator(".photo-help summary").click()
        expect(page.get_by_role("link", name="Yeni sekmede fotoğraf yükle", exact=False)).to_have_attribute(
            "target", "_blank"
        )
        assert not errors
        browser.close()
