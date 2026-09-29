from django.utils.translation import gettext_lazy as tr
import hashlib
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import User, AnonymousUser
from django.utils import timezone
from .models import AuditLog, Event, RateBucket


def audit(
    event: Event, actor: User | AnonymousUser | None, action: str, target: object = "", **metadata: object
) -> AuditLog:
    return AuditLog.objects.create(
        event=event,
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        target=str(getattr(target, "pk", target)),
        metadata=metadata,
    )


@transaction.atomic
def throttle(key: str, limit: int, seconds: int = 60) -> None:
    digest = hashlib.sha256(key.encode()).hexdigest()
    now = timezone.now()
    RateBucket.objects.get_or_create(key=digest, defaults={"expires_at": now + timedelta(seconds=seconds)})
    bucket = RateBucket.objects.select_for_update().get(pk=digest)
    if bucket.expires_at <= now:
        bucket.count = 0
        bucket.expires_at = now + timedelta(seconds=seconds)
    if bucket.count >= limit:
        raise ValidationError(tr("Too many attempts. Please wait and try again."))
    bucket.count += 1
    bucket.save()


def locked_event(event: Event) -> Event:
    return Event.objects.select_for_update().get(pk=event.pk)
