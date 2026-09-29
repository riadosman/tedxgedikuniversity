from django.utils.translation import gettext_lazy as tr
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from admissions.services import digest
from core.public_views import public_event
from core.services import throttle
from .models import ApplicationToken, VolunteerApplication
from .services import application_link, withdraw_application


def recover(request, slug):
    event = public_event(slug, request=request)

    class Form(forms.Form):
        email = forms.EmailField()

    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            throttle("volunteer-recovery:" + request.META.get("REMOTE_ADDR", ""), 20, 3600)
            email = form.cleaned_data["email"].strip().lower()
            throttle("volunteer-email:" + email, 3, 3600)
            application = VolunteerApplication.objects.filter(event=event, email=email).first()
            if application:
                application_link(application)
            return render(
                request,
                "public/message.html",
                {
                    "event": event,
                    "title": tr("Check your email"),
                    "body": tr("If that address has an application, we will send a private management link."),
                },
            )
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "public/form.html",
        {"event": event, "title": tr("Recover volunteer application"), "form": form},
    )


def access(request, slug, raw):
    event = public_event(slug, request=request)
    token = get_object_or_404(
        ApplicationToken, event=event, digest=digest(raw), expires_at__gt=timezone.now()
    )
    if request.method == "POST":
        try:
            withdraw_application(event, token)
            messages.success(
                request,
                tr("Your application has been withdrawn. Active volunteer assignments were cancelled."),
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
    token.application.refresh_from_db()
    return render(request, "public/volunteer-access.html", {"event": event, "application": token.application})
