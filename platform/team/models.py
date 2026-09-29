from django.utils.translation import gettext_lazy as tr
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from core.models import EventRecord, choices


class Department(EventRecord):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    responsibilities = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    readiness = models.CharField(
        max_length=20, choices=choices("planning", "at_risk", "ready"), default="planning"
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "name"], name="unique_department_name")]

    def __str__(self):
        return self.name


class VolunteerApplication(EventRecord):
    notification_language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    skills = models.TextField(blank=True)
    languages = models.CharField(max_length=200, blank=True)
    availability = models.TextField()
    preferred_department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=choices(
            "submitted", "review", "interview", "accepted", "rejected", "waitlisted", "withdrawn"
        ),
        default="submitted",
    )
    internal_notes = models.TextField(blank=True)
    notice_version = models.CharField(max_length=40)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "email"], name="unique_volunteer_application")
        ]

    def __str__(self):
        return self.name


class Volunteer(EventRecord):
    application = models.OneToOneField(VolunteerApplication, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    skills = models.TextField(blank=True)
    languages = models.CharField(max_length=200, blank=True)
    availability = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "email"], name="unique_volunteer_email"),
            models.UniqueConstraint(
                fields=["event", "user"], condition=Q(user__isnull=False), name="unique_volunteer_user"
            ),
        ]

    def __str__(self):
        return self.name


class Membership(EventRecord):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    volunteer = models.ForeignKey(Volunteer, on_delete=models.PROTECT, related_name="memberships")
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    responsibilities = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "volunteer"], name="unique_volunteer_department")
        ]

    def __str__(self):
        return f"{self.volunteer} / {self.department}"


class Shift(EventRecord):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    title = models.CharField(max_length=150)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="shift_positive_duration")
        ]

    def __str__(self):
        return self.title


class ShiftAssignment(EventRecord):
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT)
    volunteer = models.ForeignKey(Volunteer, on_delete=models.PROTECT)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    briefed_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=choices("assigned", "absent", "completed", "cancelled"), default="assigned"
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["shift", "volunteer"], name="unique_shift_assignment")]

    def clean(self):
        super().clean()
        if self.volunteer_id and self.shift_id and self.status != "cancelled":
            if not Membership.objects.filter(
                volunteer=self.volunteer, department=self.shift.department, active=True
            ).exists():
                raise ValidationError(tr("Assign the volunteer to this department first."))
            overlaps = (
                ShiftAssignment.objects.filter(
                    volunteer=self.volunteer,
                    shift__starts_at__lt=self.shift.ends_at,
                    shift__ends_at__gt=self.shift.starts_at,
                )
                .exclude(status="cancelled")
                .exclude(pk=self.pk)
            )
            if overlaps.exists():
                raise ValidationError(tr("This volunteer already has an overlapping shift."))

    def __str__(self):
        return f"{self.volunteer} — {self.shift}"


class ApplicationToken(EventRecord):
    application = models.ForeignKey(VolunteerApplication, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
