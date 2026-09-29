from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Event, RoleGrant
from admissions.models import TicketType


@pytest.fixture(autouse=True)
def no_local_rehearsal(settings):
    # A developer's .env must never silently bypass production timing in tests.
    settings.DEV_EVENT_REHEARSAL = False


@pytest.fixture(scope="session", autouse=True)
def current_browser_assets():
    from django.core.management import call_command

    call_command("collectstatic", interactive=False, verbosity=0)


@pytest.fixture
def event(db):
    now = timezone.now()
    item = Event.objects.create(
        name="Test fixture event",
        slug="test",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
        setup_at=now - timedelta(minutes=30),
        admission_opens_at=now - timedelta(minutes=30),
        licensed_capacity=100,
        capacity=2,
        registration_mode="first_come",
        payment_mode="free",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=1),
        promotions_cutoff=now + timedelta(minutes=30),
        policy_approved=True,
        privacy_approved=True,
        privacy_notice="Test notice",
        notice_version="test-1",
        published=True,
    )
    TicketType.objects.create(event=item, name="General", code="general")
    return item


@pytest.fixture
def organizer(event):
    user = get_user_model().objects.create_user("organizer", password="Long-test-only-password-62")
    RoleGrant.objects.create(event=event, user=user, role="organizer", reason="Test fixture")
    return user
