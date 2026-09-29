from django.utils.translation import gettext_lazy as tr
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from core.models import EventRecord, choices


class Task(EventRecord):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    priority = models.CharField(
        max_length=10, choices=choices("low", "normal", "high", "urgent"), default="normal"
    )
    status = models.CharField(
        max_length=20,
        choices=choices("not_started", "in_progress", "blocked", "needs_review", "completed", "cancelled"),
        default="not_started",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    acceptance = models.TextField(help_text=tr("What must be true before this task is complete?"))

    class Meta:
        indexes = [
            models.Index(fields=["event", "department", "status"]),
            models.Index(fields=["event", "due_at"]),
        ]

    def __str__(self):
        return self.title


class TaskDependency(EventRecord):
    task = models.ForeignKey(Task, related_name="dependencies", on_delete=models.PROTECT)
    depends_on = models.ForeignKey(Task, related_name="dependants", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "depends_on"], name="unique_task_dependency"),
            models.CheckConstraint(condition=~Q(task=F("depends_on")), name="no_self_dependency"),
        ]


class Incident(EventRecord):
    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=choices(
            "technical", "production", "attendee", "venue", "safety", "schedule", "equipment", "other"
        ),
    )
    severity = models.CharField(
        max_length=12, choices=choices("low", "medium", "high", "critical"), default="medium"
    )
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reported_incidents", on_delete=models.PROTECT
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="assigned_incidents",
        on_delete=models.PROTECT,
    )
    status = models.CharField(
        max_length=20,
        choices=choices("open", "investigating", "mitigated", "resolved", "closed"),
        default="open",
    )
    resolution = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["event", "status", "severity"])]

    def __str__(self):
        return self.title


class Comment(EventRecord):
    task = models.ForeignKey(Task, null=True, blank=True, related_name="comments", on_delete=models.PROTECT)
    incident = models.ForeignKey(
        Incident, null=True, blank=True, related_name="comments", on_delete=models.PROTECT
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(task__isnull=False, incident__isnull=True)
                | Q(task__isnull=True, incident__isnull=False),
                name="comment_one_parent",
            )
        ]


class RunbookItem(EventRecord):
    title = models.CharField(max_length=180)
    cue_at = models.DateTimeField(null=True, blank=True)
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    instructions = models.TextField()
    contingency = models.TextField(blank=True)
    audience = models.CharField(
        max_length=20, choices=choices("staff", "department", "leadership"), default="leadership"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    published_snapshot = models.JSONField(default=dict, blank=True, editable=False)

    def __str__(self):
        return self.title


class Contact(EventRecord):
    name = models.CharField(max_length=150)
    responsibility = models.CharField(max_length=180)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class RunbookAcknowledgment(EventRecord):
    item = models.ForeignKey(RunbookItem, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "user", "revision"], name="unique_runbook_acknowledgment")
        ]
