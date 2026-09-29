from django.db import models
from django.db.models.base import ModelBase
from collections.abc import Iterable
from django.db.models import Q
from django.conf import settings
from core.models import EventRecord, choices


class Attendee(EventRecord):
    notification_language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    name = models.CharField(max_length=150)
    email = models.EmailField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    survey_consent = models.BooleanField(default=False)
    notice_version = models.CharField(max_length=40)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "email"], condition=Q(email__isnull=False), name="unique_event_email"
            )
        ]
        indexes = [models.Index(fields=["event", "name"])]

    def save(
        self,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if self.email:
            self.email = self.email.strip().lower()
        super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

    def __str__(self):
        return self.name


class Registration(EventRecord):
    attendee = models.OneToOneField(Attendee, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=choices(
            "draft",
            "submitted",
            "under_review",
            "approved",
            "waitlisted",
            "rejected",
            "cancelled",
            "confirmed",
        ),
        default="submitted",
    )
    answers = models.JSONField(default=dict, blank=True)
    decision_note = models.TextField(blank=True)
    eligible_at = models.DateTimeField(null=True, blank=True)
    invitation = models.ForeignKey("core.Invitation", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        indexes = [models.Index(fields=["event", "status", "eligible_at"])]

    def __str__(self):
        return f"{self.attendee.name} — {self.get_status_display()}"


class TicketType(EventRecord):
    name = models.CharField(max_length=100)
    code = models.SlugField()
    enabled = models.BooleanField(default=True)
    counts_capacity = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "code"], name="unique_ticket_type")]

    def __str__(self):
        return self.name


class Ticket(EventRecord):
    attendee = models.OneToOneField(Attendee, on_delete=models.PROTECT)
    registration = models.OneToOneField(Registration, on_delete=models.PROTECT)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    reference = models.CharField(max_length=30, unique=True)
    status = models.CharField(
        max_length=20,
        choices=choices("registered", "checked_in", "cancelled", "expired", "created", "pending"),
        default="registered",
    )
    expires_at = models.DateTimeField()
    checked_in_at = models.DateTimeField(null=True, blank=True, editable=False)
    cancelled_at = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"{self.reference} — {self.attendee.name}"


class Credential(EventRecord):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="credentials")
    digest = models.CharField(max_length=64, unique=True)
    ciphertext = models.TextField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticket"], condition=Q(revoked_at__isnull=True), name="one_current_credential"
            )
        ]


class ActionToken(EventRecord):
    attendee = models.ForeignKey(Attendee, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=20, choices=choices("verify", "manage"))
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class CheckIn(EventRecord):
    ticket = models.OneToOneField(Ticket, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    admitted_at = models.DateTimeField()
    device = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=20, choices=choices("qr", "manual", "reconciled"))
    reason = models.CharField(max_length=250, blank=True)
    ledger_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "ledger_id"],
                condition=Q(ledger_id__isnull=False),
                name="unique_manual_ledger",
            )
        ]
        indexes = [models.Index(fields=["event", "admitted_at"])]


class ScanReceipt(EventRecord):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_id = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    result = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "actor", "request_id"], name="unique_scan_request")
        ]


class ImportBatch(EventRecord):
    digest = models.CharField(max_length=64)
    rows = models.JSONField(default=list)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "digest"], name="unique_import_batch")]


class Movement(EventRecord):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT)
    kind = models.CharField(max_length=10, choices=choices("exit", "reentry"))
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class NoticeVersion(EventRecord):
    """Immutable event notice snapshot. Contains no attendee information."""

    version_identifier = models.CharField(max_length=40)
    text = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "version_identifier"], name="unique_notice_version")
        ]


class Acknowledgement(EventRecord):
    attendee = models.ForeignKey(Attendee, on_delete=models.PROTECT, related_name="acknowledgements")
    notice = models.ForeignKey(NoticeVersion, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40, default="privacy_notice_acknowledgement", editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attendee", "notice", "kind"], name="unique_attendee_acknowledgement"
            ),
            models.CheckConstraint(
                condition=Q(kind="privacy_notice_acknowledgement"), name="acknowledgement_kind_valid"
            ),
        ]
