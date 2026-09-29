from django.utils.translation import gettext_lazy as tr
from django.conf import settings
from django.db import models
from core.models import EventRecord, choices


class Announcement(EventRecord):
    title = models.CharField(max_length=180)
    body = models.TextField()
    priority = models.CharField(
        max_length=10, choices=choices("normal", "important", "urgent"), default="normal"
    )
    audience = models.CharField(
        max_length=20,
        choices=choices("staff", "department", "leaders", "volunteers", "checkin", "speakers", "organizers"),
    )
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    publish_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.title


class AnnouncementRead(EventRecord):
    announcement = models.ForeignKey(Announcement, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["announcement", "user"], name="unique_announcement_read")
        ]


class NotificationTemplate(EventRecord):
    key = models.SlugField()
    language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    subject = models.CharField(max_length=200)
    body = models.TextField(
        help_text=tr(
            "Placeholders: {event}, {name}, {link}, {status}, {ticket_id}, {event_date}, {venue}. Plain text only."
        )
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "key", "language"], name="unique_notification_template")
        ]

    def __str__(self):
        return f"{self.key} ({self.language})"

    def clean(self):
        super().clean()
        import string
        from django.core.exceptions import ValidationError

        try:
            for text in [self.subject, self.body]:
                for _, field, spec, conversion in string.Formatter().parse(text):
                    if field is not None and (
                        field not in {"event", "name", "link", "status", "ticket_id", "event_date", "venue"}
                        or spec
                        or conversion
                    ):
                        raise ValidationError(
                            tr("Use only plain {event}, {name}, {link}, and {status} placeholders.")
                        )
        except ValueError as error:
            raise ValidationError(tr("Template braces are not balanced.")) from error


class Notification(EventRecord):
    recipient = models.EmailField()
    template_key = models.CharField(max_length=60)
    payload_ciphertext = models.TextField()
    deduplication_key = models.CharField(max_length=180, unique=True)
    status = models.CharField(
        max_length=20,
        choices=choices("pending", "sending", "sent", "failed", "suppressed"),
        default="pending",
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_reference = models.CharField(max_length=180, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"])]
