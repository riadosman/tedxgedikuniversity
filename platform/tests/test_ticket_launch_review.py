"""Launch rehearsal: decode the QR actually served to an attendee, then admit it."""

import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright

from admissions.models import CheckIn, Registration, Ticket
from admissions.services import cancel_ticket, check_in, rotate_ticket


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mode", ["first_come"])
def test_served_ticket_qr_and_existing_ticket_lookup(client, live_server, event, organizer, settings, mode):
    settings.MFA_REQUIRED = False
    settings.DEBUG = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    settings.PUBLIC_BASE_URL = live_server.url
    event.registration_mode = mode
    event.entry_mode = "online"
    event.save()
    from admissions.services import notice_digest
    data = {"name": "Ticket review attendee", "email": "launch@example.invalid", "privacy": "on",
        "notice_version": event.notice_version, "notice_hash": notice_digest(event)}
    response = client.post(reverse("register", args=[event.slug]), data)
    assert response.status_code == 302
    registration = Registration.objects.get(attendee__email=data["email"])
    ticket_link = live_server.url + response.url
    client.force_login(organizer)
    ticket = Ticket.objects.get(registration=registration)
    assert ticket.status == "registered"
    assert ticket.credentials.filter(revoked_at=None).count() == 1
    lookup = client.get(reverse("scanner-data", args=[event.slug]), {"q": ticket.reference})
    assert lookup.status_code == 200 and ticket.reference in lookup.content.decode()
    assert not CheckIn.objects.filter(ticket=ticket).exists(), "Lookup must not record entry"

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(ticket_link)
        expect(page.get_by_role("heading", name=data["name"])).to_be_visible()
        expect(page.get_by_text(ticket.reference, exact=True)).to_be_visible()
        qr = page.get_by_role("img", name="Your private admission QR code")
        expect(qr).to_be_visible()
        page.add_script_tag(url=live_server.url + "/static/vendor/jsQR.js")
        raw = page.evaluate("""async () => {
            const image = document.querySelector('img.qr'); await image.decode();
            const canvas = document.createElement('canvas');
            canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
            const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
            const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
            return jsQR(pixels.data, pixels.width, pixels.height)?.data;
        }""")
        assert raw and raw.startswith("tx2.")
        artifacts = Path(settings.ROOT_DIR) / ".local/test-artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f"ticket-launch-{mode}.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()

    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "VALID"
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "ALREADY_CHECKED_IN"
    rotate_ticket(event, organizer, ticket.pk, "Synthetic rotation")
    assert check_in(event, organizer, request_id=uuid.uuid4(), credential=raw)["code"] == "REVOKED"
    current = (
        Fernet(settings.CREDENTIAL_KEY.encode())
        .decrypt(ticket.credentials.get(revoked_at=None).ciphertext.encode())
        .decode()
    )
    assert (
        check_in(event, organizer, request_id=uuid.uuid4(), credential=current)["code"] == "ALREADY_CHECKED_IN"
    )
    cancel_ticket(event, organizer, ticket.pk, "Synthetic cancellation")
    assert client.get(ticket_link.replace(live_server.url, "") + "qr/").status_code == 404
    assert CheckIn.objects.filter(ticket=ticket).count() == 1
