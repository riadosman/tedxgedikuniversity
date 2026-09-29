from django.utils.translation import gettext_lazy as tr
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from .auth_views import create_staff_user, recent_mfa
from .views import staff_event, staff_context
from .permissions import require
from .services import audit, locked_event
from .models import RoleGrant


@login_required
def users(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "users")
    accounts = get_user_model().objects.filter(rolegrant__event=event).distinct().order_by("username")
    if request.method == "POST":
        try:
            recent_mfa(request)
            target = get_object_or_404(accounts, pk=request.POST.get("user"))
            reason = request.POST.get("reason", "").strip()
            if not reason:
                raise ValidationError(tr("Record a reason for the account change."))
            if target == request.user:
                raise ValidationError(tr("You cannot deactivate your own account here."))
            with transaction.atomic():
                locked_event(event)
                other_events = (
                    RoleGrant.objects.filter(user=target, active=True)
                    .exclude(event=event)
                    .values_list("event_id", flat=True)
                    .distinct()
                )
                from .permissions import grants
                from .models import Event

                if any(
                    not grants(request.user, other).filter(role="organizer").exists()
                    for other in Event.objects.filter(pk__in=other_events)
                ):
                    raise ValidationError(
                        tr(
                            "This account serves another event. Revoke its role here instead of changing the global account."
                        )
                    )
                if (
                    target.is_active
                    and RoleGrant.objects.filter(
                        event=event, user=target, role="organizer", active=True
                    ).exists()
                    and not RoleGrant.objects.filter(
                        event=event,
                        role="organizer",
                        active=True,
                        user__is_active=True,
                        expires_at__isnull=True,
                    )
                    .exclude(user=target)
                    .exists()
                ):
                    raise ValidationError(tr("Keep at least one active organizer."))
                target.is_active = not target.is_active
                target.save()
                audit(
                    event,
                    request.user,
                    "user.activation",
                    target,
                    active=target.is_active,
                    reason=reason[:250],
                )
            messages.success(request, tr("Account status changed. Access is rechecked on every request."))
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        return redirect("users", slug=slug)
    return render(request, "staff/users.html", staff_context(request, event, accounts=accounts))


@login_required
def invite_user(request, slug):
    return create_staff_user(request, staff_event(request, slug))


@login_required
def preview(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "pages")
    from program.models import Speaker
    from .public_views import page_content

    request.event_preview = True

    return render(
        request,
        "public/home.html",
        {
            "event": event,
            "speakers": Speaker.objects.filter(event=event).exclude(published_snapshot={}),
            "introduction": page_content(event, "about", request),
        },
    )
