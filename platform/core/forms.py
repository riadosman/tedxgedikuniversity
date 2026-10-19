from django.utils.translation import gettext_lazy as tr
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Event
from .permissions import roles, grants, scoped, ADMIN, PROGRAM
from .resources import MODEL_RESOURCES


class EventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field, forms.DateTimeField):
                field.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
                field.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
        self.fields["registration_mode"].help_text = tr(
            "Open registration issues tickets immediately within capacity. No email verification or review queue is used."
        )
        self.fields["published"].help_text = tr(
            "Makes the event public. Registration and volunteer intake have separate switches. Publish approved CMS pages separately."
        )
        self.fields["opens_at"].help_text = tr(
            "Applications are accepted only between the registration opening and closing times."
        )
        self.fields["admission_opens_at"].help_text = tr(
            "Entrance check-in opening time, not the registration opening date."
        )
        self.fields["volunteer_open"].help_text = tr(
            "Requires a published event, approved privacy notice and notice version. Attendee registration may remain closed."
        )
        self.fields["privacy_approved"].help_text = tr(
            "Select only after the privacy notice has actually been approved."
        )
        self.fields["policy_approved"].help_text = tr(
            "Select only after the registration policy has actually been approved."
        )
        self.fields["enabled_languages"].help_text = tr(
            'Supported language codes as JSON, for example ["tr", "en"]. This does not translate event content automatically.'
        )
        self.fields["retention_days"].help_text = tr(
            "Choose a retention period after event end; this is an organizer policy, not a statutory default. Erasure is a reviewed action."
        )
        self.fields["retention_reason"].help_text = tr(
            "Document TEDx survey completion, applicable obligations and dispute/audit needs before erasure."
        )
        assert isinstance(self.fields["registration_mode"], forms.ChoiceField)
        self.fields["registration_mode"].choices = [
            ("closed", tr("Closed")),
            ("first_come", tr("Open — immediate tickets")),
        ]
        self.fields["notice_version"].help_text = tr(
            "Identifier of the approved privacy notice version; update it when the notice changes."
        )
        self.fields["capacity"].help_text = tr(
            "Must respect the event licence and cannot be lower than tickets already committed."
        )

    def volunteer_steps(self):
        steps = [
            (
                "privacy_notice",
                tr("Add the privacy notice"),
                tr(
                    "Paste the approved notice shown to applicants. A title or a version number alone is not a notice."
                ),
            ),
            (
                "notice_version",
                tr("Name this notice version"),
                tr(
                    "Enter a version label, for example v1.0. This identifies the text applicants accepted; it is not an approval."
                ),
            ),
            (
                "privacy_approved",
                tr("Confirm the notice approval"),
                tr(
                    "After the responsible organizer or university has approved the text, select Privacy approved. The system does not approve it for you."
                ),
            ),
            (
                "published",
                tr("Publish the event"),
                tr("The event must be published for visitors to submit applications."),
            ),
            (
                "volunteer_open",
                tr("Open volunteer applications"),
                tr("Select Volunteer open, then save settings. You can complete all steps and save once."),
            ),
        ]
        return [
            (name, title, help_text, bool(str(self[name].value() or "").strip()))
            for name, title, help_text in steps
        ]

    def clean(self):
        data = super().clean() or {}
        if data.get("volunteer_open"):
            required = {
                "privacy_notice": tr(
                    "Paste the approved privacy notice before opening volunteer applications."
                ),
                "notice_version": tr("Enter the notice version, for example v1.0."),
                "privacy_approved": tr(
                    "Confirm approval of the privacy notice, or leave volunteer applications closed."
                ),
            }
            for name, message in required.items():
                if not data.get(name):
                    self.add_error(name, message)
        return data

    def sections(self):
        groups = [
            (tr("Event identity and location"), "name theme venue venue_confirmed map_url contact_email"),
            (
                tr("Event timing"),
                "starts_at ends_at admission_opens_at",
            ),
            (
                tr("Attendee registration and tickets"),
                "capacity registration_mode payment_mode opens_at closes_at published volunteer_open ticket_email_enabled",
            ),
            (
                tr("Privacy and approvals"),
                "privacy_notice privacy_approved terms policy_approved",
            ),
            (
                tr("Advanced settings"),
                "setup_at handover_at max_talk_minutes promotions_cutoff notice_version retention_days retention_reason enabled_languages",
            ),
        ]
        return [(title, [self[name] for name in names.split()]) for title, names in groups]

    class Meta:
        model = Event
        fields = [
            "name",
            "starts_at",
            "ends_at",
            "setup_at",
            "handover_at",
            "admission_opens_at",
            "max_talk_minutes",
            "venue",
            "venue_confirmed",
            "map_url",
            "theme",
            "contact_email",
            "capacity",
            "registration_mode",
            "payment_mode",
            "opens_at",
            "closes_at",
            "promotions_cutoff",
            "privacy_approved",
            "policy_approved",
            "privacy_notice",
            "terms",
            "notice_version",
            "volunteer_open",
            "retention_days",
            "published",
            "enabled_languages",
            "retention_reason",
            "ticket_email_enabled",
        ]


def editable_fields(resource, user, event, instance=None):
    held = roles(user, event)
    fields = list(resource.fields)
    key = MODEL_RESOURCES[resource.model]
    if (
        "organizer" in held
        or ("event_admin" in held and key in ADMIN)
        or ("speaker_manager" in held and key in PROGRAM)
        or ("editor" in held and key == "pages")
    ):
        return fields
    if key == "files":
        return fields
    if key == "departments" and "leader" in held:
        return ["readiness", "notes"]
    if "leader" in held and key in {"tasks", "incidents", "shifts", "assignments", "dependencies", "runbook"}:
        department_id = getattr(instance, "department_id", None) if instance else None
        if (
            not instance
            or (
                department_id is not None
                and grants(user, event).filter(role="leader", department_id=department_id).exists()
            )
            or key in {"assignments", "dependencies"}
        ):
            return fields
    if key == "incidents" and "technology" in held and (not instance or instance.category == "technical"):
        return fields
    allowed = {
        "tasks": {"status"},
        "volunteers": {"name", "email", "skills", "languages", "availability"},
        "incidents": {"title", "description", "category", "severity"},
        "speakers": {"name", "biography"},
        "talks": {"title", "description", "technical_requirements"},
    }
    return [f for f in fields if f in allowed.get(key, set())]


def resource_form(resource, user, event, data=None, instance=None):
    fields = editable_fields(resource, user, event, instance)
    form_class = forms.modelform_factory(resource.model, fields=fields)
    instance = instance or resource.model(event=event)
    if hasattr(instance, "reporter_id") and not instance.reporter_id:
        instance.reporter = user
    form = form_class(data=data, instance=instance)
    if resource.model.__name__ == "Attendee" and instance.pk and not instance._state.adding:
        form.fields["correction_reason"] = forms.CharField(
            max_length=250,
            label=tr("Correction reason"),
            help_text=tr("Confirm requester identity first. Do not include extra personal information."),
        )
    for name, field in form.fields.items():
        if isinstance(field, forms.DateTimeField):
            field.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            field.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
        if isinstance(field, forms.ModelChoiceField) and field.queryset is not None:
            model = field.queryset.model
            if model == get_user_model():
                field.queryset = (
                    model.objects.filter(
                        Q(rolegrant__event=event) | Q(accountinvitation__event=event), is_active=True
                    ).distinct()
                    if resource.model.__name__ == "RoleGrant"
                    else model.objects.filter(
                        is_active=True, rolegrant__in=grants_for_event(event)
                    ).distinct()
                )
            elif model in MODEL_RESOURCES:
                key = MODEL_RESOURCES[model]
                try:
                    field.queryset = scoped(model.objects.all(), user, event, key)
                except Exception:
                    field.queryset = model.objects.none()
            if name == "department" and not roles(user, event) & {"organizer", "event_admin"}:
                assert field.queryset is not None
                field.queryset = field.queryset.filter(
                    pk__in=grants(user, event).filter(role="leader").values("department_id")
                )
                # File scopes may attach to a task/talk or public image without a department.
                # The workflow validates the selected scope and all linked records.
                field.required = MODEL_RESOURCES[resource.model] != "files" and "leader" in roles(user, event)
    return form


def grants_for_event(event):
    from django.utils import timezone
    from .models import RoleGrant

    return RoleGrant.objects.filter(event=event, active=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


class ReasonForm(forms.Form):
    reason = forms.CharField(
        max_length=250, widget=forms.Textarea(attrs={"rows": 3}), label=tr("Reason / operational note")
    )


class ConditionalCharField(forms.CharField):
    """Required only when another answer asks for it; the form's clean() enforces that."""

    conditionally_required = True


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=150, label=tr("Full name"))
    email = forms.EmailField(max_length=254, label=tr("Email"))
    phone = forms.CharField(
        max_length=24,
        label=tr("Mobile phone"),
        help_text=tr("Used only to reach you about the event day."),
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
    )
    gedik_student = forms.TypedChoiceField(
        label=tr("Are you an İstanbul Gedik University student?"),
        choices=[("yes", tr("Yes")), ("no", tr("No"))],
        coerce=lambda value: value == "yes",
        widget=forms.RadioSelect,
    )
    arrives_by_car = forms.TypedChoiceField(
        label=tr("Will you come by car?"),
        choices=[("yes", tr("Yes")), ("no", tr("No"))],
        coerce=lambda value: value == "yes",
        widget=forms.RadioSelect,
    )
    vehicle_plate = ConditionalCharField(
        required=False,
        max_length=20,
        label=tr("Vehicle plate"),
        help_text=tr("Required if you come by car. We use it to reserve your parking space."),
        widget=forms.TextInput(attrs={"autocapitalize": "characters", "data-show-when-car": ""}),
    )
    privacy = forms.BooleanField(
        label=tr("I acknowledge that I have been informed through the KVKK Aydınlatma Metni.")
    )
    notice_version = forms.CharField(widget=forms.HiddenInput)
    notice_hash = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, event, *args, **kwargs):
        from admissions.services import notice_digest

        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["notice_version"].initial = event.notice_version
        self.fields["notice_hash"].initial = notice_digest(event)

    def clean_phone(self):
        from admissions.services import normalize_phone

        return normalize_phone(self.cleaned_data["phone"])

    def clean(self):
        from admissions.services import normalize_plate

        super().clean()
        cleaned = self.cleaned_data
        if cleaned.get("arrives_by_car") is True:
            try:
                cleaned["vehicle_plate"] = normalize_plate(cleaned.get("vehicle_plate", ""))
            except ValidationError as error:
                self.add_error("vehicle_plate", error)
        else:
            cleaned["vehicle_plate"] = ""
        return cleaned


class VolunteerForm(forms.Form):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()
    skills = forms.CharField(required=False, widget=forms.Textarea)
    languages = forms.CharField(required=False, max_length=200)
    availability = forms.CharField(widget=forms.Textarea)
    privacy = forms.BooleanField(label=tr("I have read the privacy notice"))

    def __init__(self, event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from team.models import Department

        self.fields["preferred_department"] = forms.ModelChoiceField(
            Department.objects.filter(event=event, active=True), required=False
        )
