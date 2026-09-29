import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.mark.django_db(transaction=True)
def test_every_language_submitter_preserves_destination(live_server, event, settings):
    settings.DEBUG = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for javascript in [True, False]:
            context = browser.new_context(
                java_script_enabled=javascript, viewport={"width": 360, "height": 800}
            )
            page = context.new_page()
            page.goto(live_server.url + f"/e/{event.slug}/faq/?lang=tr&q=kept")
            for language in ["en", "ar", "tr"]:
                page.locator(".language-menu summary").click()
                page.locator(f'.language-switch button[value="{language}"]').click()
                expect(page.locator("html")).to_have_attribute("lang", language)
                expect(page.locator("html")).to_have_attribute("dir", "rtl" if language == "ar" else "ltr")
                assert page.url == live_server.url + f"/e/{event.slug}/faq/?q=kept"
            context.close()
        browser.close()
