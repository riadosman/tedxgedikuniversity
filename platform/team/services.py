from django.utils.translation import gettext_lazy as tr
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from admissions.services import digest
from core.services import locked_event, audit
from communications.services import enqueue
from .models import ApplicationToken, Volunteer, Membership, ShiftAssignment


def application_link(application):
    raw = secrets.token_urlsafe(32)
    ApplicationToken.objects.create(
        event=application.event,
        application=application,
        digest=digest(raw),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    enqueue(
        application.event,
        application.email,
        "volunteer-access",
        {
            "name": application.name,
            "status": application.status,
            "link": f"{settings.PUBLIC_BASE_URL}/e/{application.event.slug}/volunteer-access/{raw}/",
        },
        f"volunteer-access:{secrets.token_hex(16)}",
    )


@transaction.atomic
def withdraw_application(event, token):
    event = locked_event(event)
    if token.event_id != event.pk or token.expires_at <= timezone.now():
        raise ValidationError(tr("This application link has expired."))
    application = token.application
    application.status = "withdrawn"
    application.save()
    volunteer = Volunteer.objects.filter(event=event, application=application).first()
    if volunteer:
        volunteer.active = False
        volunteer.save()
        Membership.objects.filter(event=event, volunteer=volunteer).update(active=False)
        ShiftAssignment.objects.filter(event=event, volunteer=volunteer).update(status="cancelled")
        from core.models import RoleGrant

        if volunteer.user_id is not None:
            RoleGrant.objects.filter(event=event, user_id=volunteer.user_id, role="volunteer").update(
                active=False
            )
    audit(event, None, "volunteer.withdrawn", application)
    return application
