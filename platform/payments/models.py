from django.conf import settings
from django.db import models
from core.models import EventRecord, choices


class Order(EventRecord):
    registration = models.OneToOneField("admissions.Registration", on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    provider = models.CharField(max_length=60)
    provider_reference = models.CharField(max_length=200, unique=True)
    status = models.CharField(
        max_length=20,
        choices=choices("pending", "paid", "failed", "cancelled", "refund_pending", "refunded"),
        default="pending",
    )
    reservation_expires_at = models.DateTimeField()


class PaymentEvent(EventRecord):
    provider = models.CharField(max_length=60)
    external_id = models.CharField(max_length=200)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=40)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "external_id"], name="unique_provider_event")
        ]


class Refund(EventRecord):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="requested_refunds", on_delete=models.PROTECT
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="approved_refunds",
        on_delete=models.PROTECT,
    )
    reason = models.TextField()
    amount_minor = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=choices("requested", "approved", "submitted", "completed", "failed"),
        default="requested",
    )
