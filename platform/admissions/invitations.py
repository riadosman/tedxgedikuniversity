from django.utils.translation import gettext_lazy as tr
import secrets
from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from core.models import Invitation
from core.permissions import require
from core.services import locked_event, audit
from communications.services import enqueue
from .services import digest


def create_invitation(request, event):
    require(request.user, event, "registrations", "approve")

    class Form(forms.Form):
        email = forms.EmailField()
        reason = forms.CharField(max_length=250)

    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                event = locked_event(event)
                if not event.privacy_approved or not event.policy_approved:
                    raise ValidationError(
                        tr("Approve the event's contact and admission policy before issuing invitations.")
                    )
                raw = secrets.token_urlsafe(32)
                item = Invitation.objects.create(
                    event=event,
                    email=form.cleaned_data["email"].strip().lower(),
                    token_digest=digest(raw),
                    expires_at=timezone.now() + timedelta(hours=24),
                )
                enqueue(
                    event,
                    item.email,
                    "attendee-invitation",
                    {
                        "name": "Guest",
                        "status": "invited",
                        "link": f"{settings.PUBLIC_BASE_URL}/e/{event.slug}/register/?invitation={raw}",
                    },
                    f"invitation:{item.pk}",
                )
                audit(event, request.user, "invitation.issued", item, reason=form.cleaned_data["reason"])
            messages.success(
                request,
                tr(
                    "Invitation queued. The recipient still verifies their email and receives a ticket only within capacity."
                ),
            )
            return redirect("resource-list", slug=event.slug, key="invitations")
        except ValidationError as error:
            form.add_error(None, error)
    from core.views import staff_context

    return render(
        request, "staff/form.html", staff_context(request, event, title=tr("Invite an attendee"), form=form)
    )
