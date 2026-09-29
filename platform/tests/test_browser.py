"""Real browser and real PostgreSQL; all identities live only in the isolated test DB."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from cryptography.fernet import Fernet
from playwright.sync_api import sync_playwright, expect
from django.urls import reverse
from admissions.models import Registration, Ticket, CheckIn


def database(call):
    def invoke():
        from django.db import connections

        try:
            return call()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(invoke).result()


def accessibility(page):
    script = (Path(__file__).resolve().parents[1] / "node_modules/axe-core/axe.min.js").read_text(
        encoding="utf-8"
    )
    page.evaluate(script)
    result = page.evaluate(
        "async () => await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
    )
    assert not result["violations"], [
        (item["id"], [node["target"] for node in item["nodes"]]) for item in result["violations"]
    ]


@pytest.mark.django_db(transaction=True)
def test_event_browser_rehearsal(live_server, event, organizer, settings):
    settings.MFA_REQUIRED = False
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    settings.PUBLIC_BASE_URL = live_server.url
    settings.DEBUG = True
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        attendee = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        attendee.on("pageerror", lambda error: errors.append(str(error)))
        attendee.goto(live_server.url + reverse("register", args=[event.slug]))
        expect(attendee.get_by_role("heading", name="Attend the event")).to_be_visible()
        attendee.get_by_label("Full name").fill("Browser attendee")
        attendee.get_by_label("Email:", exact=True).fill("browser@example.invalid")
        attendee.get_by_label("I acknowledge that I have been informed through the KVKK Aydınlatma Metni.").check()
        attendee.get_by_role("button", name="Get my ticket", exact=True).click()
        expect(attendee.get_by_role("heading", name="Your ticket", exact=True)).to_be_visible()
        qr_url = attendee.get_by_role("img", name="Your private admission QR code").get_attribute("src")
        accessibility(attendee)
        staff = browser.new_page(viewport={"width": 1440, "height": 1000})
        staff.on("pageerror", lambda error: errors.append(str(error)))
        staff.goto(live_server.url + "/accounts/login/")
        staff.get_by_label("Username").fill(organizer.username)
        staff.get_by_label("Password:", exact=True).fill("Long-test-only-password-62")
        staff.get_by_role("button", name="Sign in", exact=True).click()
        expect(staff.get_by_role("heading", name="Event-day dashboard")).to_be_visible()
        registration = database(lambda: Registration.objects.get(attendee__email="browser@example.invalid"))
        ticket = database(lambda: Ticket.objects.get(registration=registration))
        raw = database(
            lambda: (
                Fernet(settings.CREDENTIAL_KEY.encode())
                .decrypt(ticket.credentials.get(revoked_at=None).ciphertext.encode())
                .decode()
            )
        )
        event.entry_mode = "online"
        database(event.save)
        staff.set_viewport_size({"width": 390, "height": 844})
        staff.goto(live_server.url + reverse("scanner", args=[event.slug]))

        # Decode the actual image served on the attendee ticket page.
        decoded = staff.evaluate(
            """async (uri) => {
            const image = new Image(); image.src = uri; await image.decode();
            const canvas = document.createElement('canvas');
            canvas.width = image.width; canvas.height = image.height;
            const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
            const pixels = ctx.getImageData(0, 0, image.width, image.height);
            return jsQR(pixels.data, pixels.width, pixels.height)?.data;
        }""",
            live_server.url + qr_url,
        )
        assert decoded == raw

        def lose_response(route):
            route.fetch()
            route.abort()

        staff.route("**/check-in/scan/", lose_response)
        staff.get_by_label("QR credential or USB scanner input").fill(raw)
        staff.get_by_role("button", name="Validate & check in").click()
        expect(staff.get_by_role("status")).to_contain_text("OUTCOME UNKNOWN")
        assert database(lambda: CheckIn.objects.filter(ticket=ticket).count()) == 1
        staff.unroute("**/check-in/scan/", lose_response)
        staff.get_by_role("button", name="Retry the same request").click()
        expect(staff.get_by_role("status")).to_contain_text("ADMIT — ticket accepted")
        assert database(lambda: CheckIn.objects.filter(ticket=ticket).count()) == 1
        assert staff.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        screenshots = Path(settings.ROOT_DIR) / ".local" / "test-artifacts"
        screenshots.mkdir(parents=True, exist_ok=True)
        staff.screenshot(path=str(screenshots / "checkin-mobile.png"), full_page=True)
        accessibility(staff)
        staff.set_viewport_size({"width": 1440, "height": 1000})
        staff.goto(live_server.url + reverse("dashboard", args=[event.slug]))
        staff.screenshot(path=str(screenshots / "operations-desktop.png"), full_page=True)
        accessibility(staff)
        for route, arguments in [
            ("resource-list", [event.slug, "tasks"]),
            ("resource-create", [event.slug, "incidents"]),
            ("reports", [event.slug]),
        ]:
            staff.goto(live_server.url + reverse(route, args=arguments))
            accessibility(staff)
        for route in ["register", "volunteer-apply"]:
            attendee.goto(live_server.url + reverse(route, args=[event.slug]))
            accessibility(attendee)
        event.enabled_languages = ["en", "tr", "ar"]
        database(event.save)
        for language, direction in [("tr", "ltr"), ("ar", "rtl")]:
            staff.context.add_cookies(
                [{"name": "django_language", "value": language, "url": live_server.url}]
            )
            staff.set_viewport_size({"width": 390, "height": 844})
            staff.goto(live_server.url + reverse("dashboard", args=[event.slug]))
            expect(staff.locator("html")).to_have_attribute("dir", direction)
            assert staff.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            accessibility(staff)
            staff.screenshot(path=str(screenshots / f"dashboard-{language}-mobile.png"), full_page=True)
        staff.context.clear_cookies()
        attendee.goto(live_server.url)
        accessibility(attendee)
        assert attendee.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        attendee.screenshot(path=str(screenshots / "public-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
