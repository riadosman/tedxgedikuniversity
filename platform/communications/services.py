import json
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import get_language
from .models import Notification, NotificationTemplate, Announcement
from core.models import Event


def enqueue(
    event: Event, recipient: str | None, key: str, context: dict[str, object], deduplication_key: str
) -> Notification | None:
    if not recipient:
        return None
    from admissions.models import Attendee
    from team.models import VolunteerApplication

    language = (
        Attendee.objects.filter(event=event, email=recipient)
        .values_list("notification_language", flat=True)
        .first()
    )
    language = (
        language
        or VolunteerApplication.objects.filter(event=event, email=recipient)
        .values_list("notification_language", flat=True)
        .first()
    )
    language = language or get_language() or "en"
    language = language if language in event.enabled_languages else "en"
    payload = (
        Fernet(settings.CREDENTIAL_KEY.encode())
        .encrypt(json.dumps({**context, "_language": language}).encode())
        .decode()
    )
    return Notification.objects.get_or_create(
        deduplication_key=deduplication_key,
        defaults={
            "event": event,
            "recipient": recipient,
            "template_key": key,
            "payload_ciphertext": payload,
            "next_attempt_at": timezone.now(),
        },
    )[0]


def deliver_batch(limit: int = 50) -> int:
    """Lease short DB transactions; never hold row locks while contacting SMTP."""
    if not getattr(settings, "OUTGOING_EMAIL_ENABLED", True):
        return 0
    delivered = 0
    for _ in range(limit):
        now = timezone.now()
        with transaction.atomic():
            job = (
                Notification.objects.select_for_update(skip_locked=True)
                .filter(
                    Q(status="pending", next_attempt_at__lte=now) | Q(status="sending", lease_until__lt=now)
                )
                .order_by("created_at")
                .first()
            )
            if not job:
                break
            job.status = "sending"
            job.lease_until = now + timedelta(minutes=5)
            job.attempts += 1
            job.save()
        try:
            context = json.loads(
                Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(job.payload_ciphertext.encode())
            )
            language = context.pop("_language", "en")
            template = NotificationTemplate.objects.get(
                event=job.event, key=job.template_key, language=language
            )
            context["event"] = job.event.name
            if not Notification.objects.filter(pk=job.pk, status="sending", attempts=job.attempts).exists():
                continue
            message = EmailMessage(
                template.subject.format_map(context),
                template.body.format_map(context),
                settings.DEFAULT_FROM_EMAIL,
                [job.recipient],
                headers={"X-Event-Delivery-ID": str(job.pk)},
            )
            if message.send() != 1:
                raise RuntimeError("backend_not_accepted")
        except Exception as error:
            # Never log SMTP responses, recipient addresses or token-bearing message text.
            Notification.objects.filter(pk=job.pk, status="sending", attempts=job.attempts).update(
                status="failed" if job.attempts >= 5 else "pending",
                next_attempt_at=now + timedelta(seconds=min(3600, 30 * 2**job.attempts)),
                last_error_code=type(error).__name__,
                lease_until=None,
            )
        else:
            Notification.objects.filter(pk=job.pk, status="sending", attempts=job.attempts).update(
                status="sent", sent_at=timezone.now(), lease_until=None, last_error_code=""
            )
            delivered += 1
    return delivered


def queue_announcement(announcement: Announcement) -> int:
    from django.contrib.auth import get_user_model
    from core.forms import grants_for_event
    from core.permissions import grants
    from team.models import Membership

    users = (
        get_user_model()
        .objects.filter(is_active=True, rolegrant__in=grants_for_event(announcement.event))
        .exclude(email="")
        .distinct()
    )
    audience_roles = {
        "leaders": "leader",
        "volunteers": "volunteer",
        "checkin": "checkin",
        "speakers": "speaker",
        "organizers": "organizer",
    }
    count = 0
    for user in users:
        targeted = announcement.audience == "staff"
        if announcement.audience in audience_roles:
            targeted = (
                grants(user, announcement.event).filter(role=audience_roles[announcement.audience]).exists()
            )
        if announcement.audience == "department":
            targeted = (
                grants(user, announcement.event)
                .filter(role="leader", department=announcement.department)
                .exists()
                or Membership.objects.filter(
                    event=announcement.event,
                    department=announcement.department,
                    volunteer__user=user,
                    active=True,
                ).exists()
            )
        if targeted:
            job = enqueue(
                announcement.event,
                user.email,
                "announcement",
                {
                    "name": user.first_name or user.username,
                    "status": announcement.title + "\n\n" + announcement.body,
                    "link": f"{settings.PUBLIC_BASE_URL}/staff/{announcement.event.slug}/announcements/{announcement.pk}/",
                },
                f"announcement:{announcement.pk}:{announcement.version}:{user.pk}",
            )
            if job and announcement.publish_at > timezone.now():
                job.next_attempt_at = announcement.publish_at
                job.save()
            count += 1
    return count
