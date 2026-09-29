from django.conf import settings
from django.db import models
from django.db.models import Q, F
from core.models import EventRecord, choices


class Speaker(EventRecord):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    biography = models.TextField(blank=True)
    language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    photo = models.ForeignKey("documents.Document", null=True, blank=True, on_delete=models.PROTECT)
    internal_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=choices("proposed", "invited", "confirmed", "withdrawn"), default="proposed"
    )
    publication_consent = models.BooleanField(default=False)
    published_snapshot = models.JSONField(default=dict, blank=True, editable=False)

    def __str__(self):
        return self.name


class Talk(EventRecord):
    speaker = models.ForeignKey(Speaker, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    technical_requirements = models.TextField(blank=True)
    fact_check_notes = models.TextField(blank=True)
    rights_notes = models.TextField(blank=True)
    release_received = models.BooleanField(default=False)
    fact_checked = models.BooleanField(default=False)
    rights_cleared = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=choices("draft", "review", "changes_required", "ready", "approved", "withdrawn"),
        default="draft",
    )

    def __str__(self):
        return self.title


class Rehearsal(EventRecord):
    talk = models.ForeignKey(Talk, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="rehearsal_positive_duration"
            )
        ]


class ScheduleItem(EventRecord):
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20, choices=choices("opening", "talk", "break", "transition", "closing", "production")
    )
    talk = models.ForeignKey(Talk, null=True, blank=True, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    internal_cues = models.TextField(blank=True)
    public_description = models.TextField(blank=True)
    published_snapshot = models.JSONField(default=dict, blank=True, editable=False)

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="schedule_positive_duration")
        ]
        indexes = [models.Index(fields=["event", "starts_at"])]

    def __str__(self):
        return self.title
