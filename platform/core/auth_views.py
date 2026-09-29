from django.utils.translation import gettext_lazy as tr
import io
import time
import qrcode
from qrcode.image.pil import PilImage
from django import forms
from django.contrib import messages
from django.contrib.auth import views as auth_views, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from .services import throttle, audit
from .models import RoleGrant, AccountInvitation
from .dev_access import DEV_USERNAME, DEV_SESSION_KEY, local_development_access_allowed, development_session
from django.views.decorators.http import require_POST


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["development_login_available"] = local_development_access_allowed(self.request)
        return context

    def form_valid(self, form):
        throttle("login:" + self.request.META.get("REMOTE_ADDR", ""), 500, 900)
        response = super().form_valid(form)
        assert self.request.user.pk is not None
        for grant in RoleGrant.objects.filter(user_id=self.request.user.pk, active=True).select_related(
            "event"
        )[:1]:
            audit(grant.event, self.request.user, "auth.login")
        return response

    def form_invalid(self, form):
        try:
            throttle("login:" + self.request.META.get("REMOTE_ADDR", ""), 500, 900)
        except ValidationError:
            form.add_error(None, tr("Too many login attempts. Try again later."))
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        try:
            throttle("login-gate:" + request.META.get("REMOTE_ADDR", ""), 500, 900)
            throttle("login-identity:" + request.POST.get("username", "").casefold()[:150], 10, 900)
            return super().post(request, *args, **kwargs)
        except ValidationError:
            return render(
                request, self.template_name, {"form": self.get_form(), "throttled": True}, status=429
            )


@require_POST
def development_login(request):
    from django.conf import settings
    from .models import Event

    if not local_development_access_allowed(request):
        raise Http404
    with transaction.atomic():
        event = Event.objects.select_for_update().filter(slug=settings.DEV_LOGIN_EVENT).first()
        if event is None:
            raise Http404
        user, created = get_user_model().objects.get_or_create(username=DEV_USERNAME)
        if created:
            user.first_name = "Yerel geliştirme"
            user.set_unusable_password()
            user.save()
        elif not user.is_active or user.has_usable_password() or user.is_superuser:
            raise PermissionDenied
        grant, created = RoleGrant.objects.get_or_create(
            event=event,
            user=user,
            role="organizer",
            department=None,
            defaults={"reason": "Explicit localhost-only development access"},
        )
        if not grant.active or grant.expires_at is not None:
            raise PermissionDenied
        audit(event, user, "auth.development_login", user)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session[DEV_SESSION_KEY] = user.pk
    request.session["session_started"] = time.time()
    request.session["last_activity"] = time.time()
    return redirect("dashboard", slug=event.slug)


class CodeForm(forms.Form):
    code = forms.CharField(
        max_length=32, widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"})
    )


@login_required
def mfa(request):
    confirmed = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    device = confirmed or TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    if request.method == "POST" and request.POST.get("action") == "enroll" and not confirmed:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if not TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
                device, _ = TOTPDevice.objects.get_or_create(
                    user=request.user, name="Authenticator", confirmed=False
                )
        return redirect("mfa")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid() and device:
        try:
            throttle(f"mfa:{request.user.pk}", 10, 300)
            with transaction.atomic():
                device = TOTPDevice.objects.select_for_update().get(pk=device.pk)
                valid = device.verify_token(form.cleaned_data["code"])
                if not valid and confirmed:
                    recovery = StaticDevice.objects.filter(user=request.user, confirmed=True).first()
                    valid = recovery and recovery.verify_token(form.cleaned_data["code"])
                if valid:
                    new = not device.confirmed
                    device.confirmed = True
                    device.save()
                    otp_login(request, device)
                    request.session["mfa_at"] = time.time()
                    if new:
                        recovery = StaticDevice.objects.create(user=request.user, name="Recovery")
                        codes = [StaticToken.random_token() for _ in range(8)]
                        for code in codes:
                            StaticToken.objects.create(device=recovery, token=code)
                        return render(request, "registration/recovery.html", {"codes": codes})
                    return redirect("staff-home")
                form.add_error(
                    "code", tr("Invalid or already-used code. Wait for the next code and try again.")
                )
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request, "registration/mfa.html", {"form": form, "device": device, "enrolling": not confirmed}
    )


@login_required
def mfa_qr(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).last()
    if not device:
        raise PermissionDenied
    image = qrcode.make(device.config_url, image_factory=PilImage)
    data = io.BytesIO()
    image.save(data, format="PNG")
    return HttpResponse(data.getvalue(), content_type="image/png")


class StaffUserForm(forms.Form):
    username = forms.CharField(max_length=150, label=tr("Username"))
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False, label=tr("First name"))
    last_name = forms.CharField(max_length=150, required=False, label=tr("Last name"))


def recent_mfa(request):
    from django.conf import settings

    if development_session(request):
        return
    if settings.MFA_REQUIRED and time.time() - request.session.get("mfa_at", 0) > 300:
        raise ValidationError(tr("Verify your authenticator again before this privileged action."))


def create_staff_user(request, event):
    from .permissions import require

    require(request.user, event, "users", "create")
    form = StaffUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            recent_mfa(request)
            with transaction.atomic():
                data = form.cleaned_data
                if get_user_model().objects.filter(username=data["username"]).exists():
                    raise ValidationError(tr("This username already exists."))
                user = get_user_model().objects.create_user(**data)
                user.set_unusable_password()
                user.save()
                AccountInvitation.objects.create(event=event, user=user, invited_by=request.user)
                # Separate explicit role assignment is required before any event access.
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.conf import settings
                from communications.services import enqueue

                link = f"{settings.PUBLIC_BASE_URL}/accounts/reset/{urlsafe_base64_encode(force_bytes(user.pk))}/{default_token_generator.make_token(user)}/"
                enqueue(
                    event,
                    user.email,
                    "account-invitation",
                    {"name": user.first_name or user.username, "link": link, "status": ""},
                    f"user-invite:{user.pk}",
                )
                audit(event, request.user, "user.invited", user)
            messages.success(
                request, tr("Account invitation queued. Assign the appropriate event role next.")
            )
            return redirect("resource-list", slug=event.slug, key="roles")
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request, "staff/form.html", {"form": form, "event": event, "title": tr("Invite a staff member")}
    )


def recover_password(request):
    class Form(forms.Form):
        email = forms.EmailField()

    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            email = form.cleaned_data["email"].strip().lower()
            throttle("password-recovery-ip:" + request.META.get("REMOTE_ADDR", ""), 30, 3600)
            throttle("password-recovery-email:" + email, 3, 3600)
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.conf import settings
            from communications.services import enqueue
            import uuid

            for user in get_user_model().objects.filter(email__iexact=email, is_active=True):
                grant = RoleGrant.objects.filter(user=user, active=True).select_related("event").first()
                invitation = AccountInvitation.objects.filter(user=user).select_related("event").first()
                event = grant.event if grant else invitation.event if invitation else None
                if event:
                    link = f"{settings.PUBLIC_BASE_URL}/accounts/reset/{urlsafe_base64_encode(force_bytes(user.pk))}/{default_token_generator.make_token(user)}/"
                    enqueue(
                        event,
                        user.email,
                        "account-invitation",
                        {"name": user.first_name or user.username, "link": link, "status": ""},
                        f"password-recovery:{uuid.uuid4()}",
                    )
            return render(
                request,
                "public/message.html",
                {
                    "title": tr("Check your email"),
                    "body": tr(
                        "If that address has an eligible account, we will send a password reset link. Your authenticator remains required."
                    ),
                },
            )
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "registration/recover.html", {"form": form})
