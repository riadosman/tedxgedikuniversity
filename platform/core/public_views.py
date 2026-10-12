from django.utils.translation import gettext_lazy as tr
import io
from cryptography.fernet import Fernet
import qrcode
from qrcode.image.pil import PilImage
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.http import HttpResponse, Http404
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Event, Page
from .forms import RegistrationForm, VolunteerForm
from .services import throttle, audit, locked_event
from .models import PrivacyRequest
from admissions.models import ActionToken, Ticket, Attendee
from admissions.services import (
    submit_registration,
    digest,
    new_action_token,
    queue_ticket_email,
    cancel_ticket,
)
from program.models import Speaker, ScheduleItem


def public_event(slug=None, *, request=None):
    local_preview = settings.DEBUG and settings.LOCAL_EVENT_PREVIEW and not settings.PRODUCTION
    qs = Event.objects.all() if local_preview else Event.objects.filter(published=True)
    event = get_object_or_404(qs, slug=slug) if slug else qs.first()
    if request is not None:
        request.event_preview = bool(event and not event.published)
        if request.event_preview and request.method not in {"GET", "HEAD"}:
            raise PermissionDenied("Unpublished event preview is read-only.")
    return event


def home(request):
    event = public_event(request=request)
    if not event:
        return render(request, "public/unpublished.html")
    return render(
        request,
        "public/home.html",
        {
            "event": event,
            "speakers": Speaker.objects.filter(event=event).exclude(published_snapshot={})[:8],
            "introduction": page_content(event, "about", request),
            "days_left": days_until(event),
        },
    )


def days_until(event):
    """Calendar days to the event day in event time: 0 on the day itself, None afterwards."""
    days = (timezone.localdate(event.starts_at) - timezone.localdate()).days
    return days if days >= 0 else None


def page_content(event, key, request):
    language = request.LANGUAGE_CODE if request.LANGUAGE_CODE in event.enabled_languages else "en"
    if getattr(request, "event_preview", False):
        draft = Page.objects.filter(event=event, key=key, language=language).first()
        if draft:
            return {"title": draft.title, "body": draft.body}
    content = (
        Page.objects.filter(event=event, key=key, language=language).exclude(published_snapshot={}).first()
    )
    if not content and language != "en":
        content = (
            Page.objects.filter(event=event, key=key, language="en").exclude(published_snapshot={}).first()
        )
    return content.published_snapshot if content else None


def attendance_rules(event, request):
    """Organizer-edited rules page plus the door time from event settings."""
    doors = (
        tr("Doors open at %(time)s.")
        % {"time": timezone.localtime(event.admission_opens_at).strftime("%H:%M")}
        if event.admission_opens_at
        else ""
    )
    return {"rules": page_content(event, "rules", request), "doors_open": doors}


def page(request, slug, key):
    event = public_event(slug, request=request)
    if key not in {"about", "theme", "speakers", "program", "venue", "faq", "contact", "privacy", "terms"}:
        custom_pages = Page.objects.filter(event=event, key=key)
        if not getattr(request, "event_preview", False):
            custom_pages = custom_pages.exclude(published_snapshot={})
        if not custom_pages.exists():
            raise Http404
    content = page_content(event, key, request)
    if key == "privacy" and not getattr(request, "event_preview", False):
        content = (
            {"title": "KVKK Aydınlatma Metni", "body": event.privacy_notice}
            if event.privacy_approved
            else None
        )
    titles = {
        "about": tr("About"),
        "theme": tr("Theme"),
        "speakers": tr("Speakers"),
        "program": tr("Program"),
        "venue": tr("Venue"),
        "faq": tr("FAQ"),
        "contact": tr("Contact"),
        "privacy": tr("Privacy"),
        "terms": tr("Terms"),
    }
    context = {
        "event": event,
        "key": key,
        "content": content,
        "title": titles.get(key, key.replace("-", " ").title()),
    }
    context["subtitle"] = {
        "about": tr("One day. New ideas. Shared perspectives."),
        "theme": tr("The ideas that bring us together."),
        "speakers": tr("Meet the people behind the ideas."),
        "program": tr("Your day, at a glance."),
        "venue": tr("Everything you need to find your way here."),
        "faq": tr("A little clarity before you join us."),
        "contact": tr("Questions about joining us? Start here."),
        "privacy": tr("Your information, explained clearly."),
        "terms": tr("What to know before taking part."),
    }.get(key, "")
    if key == "faq" and content:
        context["faq_sections"] = []
        for paragraph in content.get("body", "").replace("\r\n", "\n").split("\n\n"):
            if paragraph.strip():
                question, _, answer = paragraph.strip().partition("\n")
                context["faq_sections"].append({"question": question, "answer": answer})
    if key in {"speakers", "about"}:
        context["speakers"] = Speaker.objects.filter(event=event).exclude(published_snapshot={})
    if key in {"program", "about"}:
        context["schedule"] = (
            ScheduleItem.objects.filter(event=event).exclude(published_snapshot={}).order_by("starts_at")
        )
    return render(request, "public/page.html", context)


def speaker(request, slug, pk):
    event = public_event(slug, request=request)
    item = get_object_or_404(Speaker.objects.filter(event=event).exclude(published_snapshot={}), pk=pk)
    return render(request, "public/speaker.html", {"event": event, "speaker": item.published_snapshot})


def register(request, slug):
    event = public_event(slug, request=request)
    from admissions.services import ensure_intake

    closed_reason = ""
    try:
        ensure_intake(event)
    except ValidationError as error:
        closed_reason = " ".join(error.messages)
    form = RegistrationForm(event, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            throttle("register:" + request.META.get("REMOTE_ADDR", ""), 20, 3600)
            throttle("register-email:" + form.cleaned_data["email"].lower(), 3, 3600)
            with transaction.atomic():
                registration = submit_registration(
                    event,
                    name=form.cleaned_data["name"],
                    email=form.cleaned_data["email"],
                    privacy_acknowledged=form.cleaned_data["privacy"],
                    notice_version=form.cleaned_data["notice_version"],
                    notice_hash=form.cleaned_data["notice_hash"],
                    phone=form.cleaned_data["phone"],
                    arrives_by_car=form.cleaned_data["arrives_by_car"],
                    vehicle_plate=form.cleaned_data["vehicle_plate"],
                )
                raw = new_action_token(registration.attendee)
            return redirect("ticket-access", slug=event.slug, raw=raw)
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "public/register.html",
        {
            "event": event,
            "title": tr("Attend the event"),
            "introduction": page_content(event, "registration", request),
            "form": form,
            "closed": bool(closed_reason),
            "closed_reason": closed_reason,
            "registration_upcoming": bool(event.opens_at and event.opens_at > timezone.now()),
            "notice": event.privacy_notice if event.privacy_approved else "",
            **attendance_rules(event, request),
        },
    )


def volunteer(request, slug):
    event = public_event(slug, request=request)
    form = VolunteerForm(event, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            throttle("volunteer:" + request.META.get("REMOTE_ADDR", ""), 5, 3600)
            with transaction.atomic():
                event = locked_event(event)
                if (
                    not event.published
                    or not event.volunteer_open
                    or not event.privacy_approved
                    or not event.notice_version
                    or not event.privacy_notice
                ):
                    raise ValidationError(tr("Volunteer applications are not open."))
                from team.models import VolunteerApplication

                data = {k: v for k, v in form.cleaned_data.items() if k != "privacy"}
                data["email"] = data["email"].strip().lower()
                data["notification_language"] = (
                    request.LANGUAGE_CODE if request.LANGUAGE_CODE in event.enabled_languages else "en"
                )
                item, created = VolunteerApplication.objects.get_or_create(
                    event=event,
                    email=data.pop("email"),
                    defaults={**data, "notice_version": event.notice_version},
                )
                if created:
                    audit(event, None, "volunteer.applied", item)
                    from team.services import application_link

                    application_link(item)
            return render(
                request,
                "public/message.html",
                {
                    "event": event,
                    "title": tr("Application received"),
                    "body": tr(
                        "Thank you. The volunteer team will review eligible applications and contact you."
                    ),
                },
            )
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "public/form.html",
        {
            "event": event,
            "title": tr("Join the volunteer team"),
            "introduction": page_content(event, "volunteering", request),
            "form": form,
            "closed": not event.published or not event.volunteer_open,
            "notice": event.privacy_notice,
        },
    )


def access(request, slug, raw):
    event = public_event(slug, request=request)
    token = ActionToken.objects.filter(
        event=event, digest=digest(raw), used_at__isnull=True, expires_at__gt=timezone.now()
    ).first()
    if not token:
        return render(
            request,
            "public/message.html",
            {
                "event": event,
                "title": tr("Link unavailable"),
                "body": tr(
                    "This link has expired or has already been used. Request a fresh email from the ticket recovery page."
                ),
            },
            status=400,
        )
    if token.purpose != "manage":
        return render(
            request,
            "public/message.html",
            {
                "event": event,
                "title": tr("Registration has changed"),
                "body": tr(
                    "Email verification no longer issues tickets. Contact the organizing team about your earlier application."
                ),
            },
            status=410,
        )
    if request.method == "POST":
        try:
            throttle("token:" + request.META.get("REMOTE_ADDR", ""), 30, 300)
            if request.POST.get("action") == "cancel":
                cancelled_ticket = get_object_or_404(Ticket, event=event, attendee=token.attendee)
                cancel_ticket(
                    event,
                    None,
                    cancelled_ticket.pk,
                    "Attendee self-service cancellation",
                    attendee=token.attendee,
                )
                messages.success(request, tr("Your ticket has been cancelled."))
            elif request.POST.get("action") == "profile":
                name = request.POST.get("name", "").strip()
                if not 1 <= len(name) <= 150:
                    raise ValidationError(tr("Enter a name of 1–150 characters."))
                with transaction.atomic():
                    token.attendee.name = name
                    token.attendee.save()
                    audit(
                        event,
                        None,
                        "attendee.self_corrected",
                        token.attendee,
                    )
                messages.success(request, tr("Your name was updated."))
            elif request.POST.get("action") == "export":
                registration = token.attendee.registration
                return JsonResponse(
                    {
                        "name": token.attendee.name,
                        "email": token.attendee.email,
                        "phone": token.attendee.phone,
                        "arrives_by_car": token.attendee.arrives_by_car,
                        "vehicle_plate": token.attendee.vehicle_plate,
                        "notice_version": token.attendee.notice_version,
                        "registration_status": registration.status,
                        "answers": registration.answers,
                    }
                )
            elif request.POST.get("action") == "erase":
                with transaction.atomic():
                    item = PrivacyRequest.objects.create(
                        event=event,
                        email=token.attendee.email or "",
                        kind="erase",
                        status="verified",
                        resolution="Submitted through verified attendee management link.",
                    )
                    audit(event, None, "privacy.requested", item)
                messages.success(request, tr("Your verified erasure request has been recorded for review."))
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
    ticket = (
        Ticket.objects.filter(event=event, attendee=token.attendee).first()
        if token.purpose == "manage"
        else None
    )
    return render(
        request,
        "public/ticket.html",
        {"event": event, "token": token, "ticket": ticket, "raw": raw, **attendance_rules(event, request)},
    )


def ticket_qr(request, slug, raw):
    event = public_event(slug, request=request)
    token = get_object_or_404(
        ActionToken,
        event=event,
        digest=digest(raw),
        purpose="manage",
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    ticket = get_object_or_404(
        Ticket,
        event=event,
        attendee=token.attendee,
        status__in=["registered", "checked_in"],
        expires_at__gt=timezone.now(),
    )
    credential = ticket.credentials.filter(revoked_at__isnull=True).first()
    if not credential:
        raise Http404
    raw_qr = Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(credential.ciphertext.encode()).decode()
    data = io.BytesIO()
    qrcode.make(raw_qr, image_factory=PilImage).save(data, format="PNG")
    response = HttpResponse(data.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store, private"
    return response


def recover(request, slug):
    event = public_event(slug, request=request)

    class RecoveryForm(forms.Form):
        email = forms.EmailField()

    form = RecoveryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            throttle("recover:" + request.META.get("REMOTE_ADDR", ""), 6, 3600)
            email = form.cleaned_data["email"].lower().strip()
            throttle("recover-address:" + email, 3, 3600)
            attendee = Attendee.objects.filter(event=event, email=email).first()
            if attendee and Ticket.objects.filter(attendee=attendee).exists():
                queue_ticket_email(attendee.pk, "ticket-access")
            return render(
                request,
                "public/message.html",
                {
                    "event": event,
                    "title": tr("Check your email"),
                    "body": tr(
                        "If ticket email is enabled and this address has a ticket, a fresh link will be sent. Otherwise contact the organizing team for assistance."
                    ),
                },
            )
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request, "public/form.html", {"event": event, "form": form, "title": tr("Recover your ticket link")}
    )
