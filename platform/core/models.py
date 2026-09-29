from __future__ import annotations
from django.utils.translation import gettext_lazy as tr

import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.utils.functional import _StrPromise
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.db.models import Q, F


def choices(*values: str) -> list[tuple[str, _StrPromise]]:
    return [(v, tr(v.replace("_", " ").title())) for v in values]


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(
        self,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.full_clean()
        super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

    def __str__(self):
        return str(
            getattr(self, "title", None)
            or getattr(self, "name", None)
            or f"{str(self._meta.verbose_name or 'Record').title()} · {str(self.pk)[:8]}"
        )


class Event(Record):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    setup_at = models.DateTimeField(null=True, blank=True)
    handover_at = models.DateTimeField(null=True, blank=True)
    admission_opens_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=60, default="Europe/Istanbul")
    venue = models.CharField(max_length=240, blank=True)
    venue_confirmed = models.BooleanField(default=False)
    map_url = models.URLField(blank=True)
    theme = models.CharField(max_length=240, blank=True)
    contact_email = models.EmailField(blank=True)
    licensed_capacity = models.PositiveIntegerField()
    max_talk_minutes = models.PositiveIntegerField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    registration_mode = models.CharField(
        max_length=20, choices=choices("closed", "first_come"), default="closed"
    )
    payment_mode = models.CharField(
        max_length=20, choices=choices("undecided", "free", "paid"), default="undecided"
    )
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    promotions_cutoff = models.DateTimeField(null=True, blank=True)
    entry_mode = models.CharField(
        max_length=20, choices=choices("closed", "online", "manual", "reconciling"), default="closed"
    )
    privacy_approved = models.BooleanField(default=False)
    policy_approved = models.BooleanField(default=False)
    volunteer_open = models.BooleanField(default=False)
    privacy_notice = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    notice_version = models.CharField(max_length=40, blank=True)
    retention_days = models.PositiveIntegerField(null=True, blank=True)
    retention_reason = models.CharField(max_length=250, blank=True)
    ticket_email_enabled = models.BooleanField(default=False)
    source = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    enabled_languages = models.JSONField(default=list, blank=True)
    registration_fields = models.JSONField(default=list, blank=True)
    required_registration_fields = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="event_positive_duration"),
            models.CheckConstraint(
                condition=Q(capacity__lte=F("licensed_capacity")), name="event_capacity_ceiling"
            ),
        ]

    def clean(self):
        if self.volunteer_open and not (
            self.privacy_approved and self.privacy_notice and self.notice_version
        ):
            raise ValidationError(
                tr("Approve a versioned privacy notice before opening volunteer applications.")
            )
        if self.admission_opens_at and (
            self.admission_opens_at >= self.ends_at
            or (self.setup_at and self.admission_opens_at < self.setup_at)
        ):
            raise ValidationError(
                tr("Entrance opening must be after venue setup access and before the event ends.")
            )
        if not isinstance(self.enabled_languages, list) or any(
            language not in {"en", "tr", "ar"} for language in self.enabled_languages
        ):
            raise ValidationError(tr("Choose supported language codes: en, tr, ar."))
        if self.registration_mode != "closed":
            if not self.policy_approved:
                raise ValidationError(tr("Approve registration policy before opening registration."))
            if self.privacy_approved and not (self.privacy_notice and self.notice_version):
                raise ValidationError(tr("An approved privacy notice needs its text and version."))
            if (
                self.payment_mode == "undecided"
                or not self.opens_at
                or not self.closes_at
                or not self.capacity
            ):
                raise ValidationError(tr("Set admission mode, capacity and registration dates first."))
        if self.privacy_approved and not self._state.adding:
            from admissions.models import NoticeVersion

            historical = NoticeVersion.objects.filter(
                event=self, version_identifier=self.notice_version
            ).first()
            if historical and historical.text != self.privacy_notice:
                raise ValidationError(tr("Use a new notice version when changing published notice text."))
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError(tr("Registration closes after it opens."))
        if not isinstance(self.registration_fields, list) or len(self.registration_fields) > 12:
            raise ValidationError(tr("Use at most 12 optional form fields."))
        keys = set()
        for field in self.registration_fields:
            if not isinstance(field, dict) or set(field) - {"key", "label", "type", "required", "options"}:
                raise ValidationError(tr("Invalid custom-field definition."))
            key = field.get("key", "")
            if (
                not key.isidentifier()
                or key in keys
                or len(key) > 40
                or field.get("type") not in {"text", "choice", "boolean"}
            ):
                raise ValidationError(tr("Custom fields need unique keys, labels and supported types."))
            if not field.get("label") or len(field["label"]) > 150:
                raise ValidationError(tr("Each field needs a concise label."))
            if field["type"] == "choice" and (
                not isinstance(field.get("options"), list)
                or not 1 <= len(field["options"]) <= 50
                or any(
                    not isinstance(option, str) or not 1 <= len(option) <= 100 for option in field["options"]
                )
            ):
                raise ValidationError(tr("Choice fields need 1–50 text options of at most 100 characters."))
            keys.add(key)

    def __str__(self):
        return self.name


class EventRecord(Record):
    event = models.ForeignKey(Event, on_delete=models.PROTECT)

    class Meta(Record.Meta):
        abstract = True

    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if (
                isinstance(field, models.ForeignKey)
                and field.name != "event"
                and getattr(self, field.attname, None)
            ):
                target = getattr(self, field.name)
                if hasattr(target, "event_id") and target.event_id != self.event_id:
                    raise ValidationError({field.name: "This record belongs to a different event."})


class RoleGrant(EventRecord):
    ROLES = choices(
        "organizer",
        "event_admin",
        "technology",
        "leader",
        "volunteer",
        "checkin",
        "speaker_manager",
        "editor",
        "finance",
        "speaker",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=30, choices=ROLES)
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=250)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user", "role", "department"], name="unique_scoped_role"
            ),
            models.UniqueConstraint(
                fields=["event", "user", "role"],
                condition=Q(department__isnull=True),
                name="unique_event_role",
            ),
            models.CheckConstraint(
                condition=~Q(role="leader") | Q(department__isnull=False), name="leader_requires_department"
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"


class AuditLog(EventRecord):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["event", "created_at"]), models.Index(fields=["event", "target"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(tr("Audit records are append-only."))
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(tr("Audit records cannot be deleted through the application."))


class Page(EventRecord):
    key = models.SlugField()
    language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    title = models.CharField(max_length=180)
    body = models.TextField()
    source = models.TextField(blank=True)
    published_snapshot = models.JSONField(default=dict, blank=True, editable=False)
    published_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "key", "language"], name="unique_page_locale")
        ]

    def __str__(self):
        return f"{self.title} ({self.language})"


class ContentRevision(EventRecord):
    page = models.ForeignKey(Page, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Invitation(EventRecord):
    email = models.EmailField()
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class RateBucket(models.Model):
    key = models.CharField(primary_key=True, max_length=64)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class PrivacyRequest(EventRecord):
    email = models.EmailField()
    kind = models.CharField(max_length=20, choices=choices("access", "correct", "erase", "withdraw"))
    status = models.CharField(
        max_length=20, choices=choices("received", "verified", "resolved", "declined"), default="received"
    )
    resolution = models.TextField(blank=True)
    hold_until = models.DateTimeField(null=True, blank=True)


class AccountInvitation(EventRecord):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="sent_event_invitations", on_delete=models.PROTECT
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="unique_staff_invitation")]
