from django.conf import settings
from django.db import models
from core.models import EventRecord, choices


class Document(EventRecord):
    title = models.CharField(max_length=180)
    original_name = models.CharField(max_length=180)
    storage_key = models.CharField(max_length=240, unique=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    department = models.ForeignKey("team.Department", null=True, blank=True, on_delete=models.PROTECT)
    task = models.ForeignKey("operations.Task", null=True, blank=True, on_delete=models.PROTECT)
    talk = models.ForeignKey("program.Talk", null=True, blank=True, on_delete=models.PROTECT)
    scope = models.CharField(
        max_length=20,
        choices=choices("leadership", "department", "task", "speaker", "public_candidate"),
        default="leadership",
    )
    scan_status = models.CharField(
        max_length=20, choices=choices("quarantined", "clean", "rejected"), default="quarantined"
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
