"""Provider boundary. No selected provider means paid checkout is unavailable."""

from django.utils.translation import gettext_lazy as tr

from dataclasses import dataclass
from typing import Protocol
from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class VerifiedPayment:
    event_id: str
    external_id: str
    order_reference: str
    amount_minor: int
    currency: str
    status: str


class PaymentProvider(Protocol):
    def create_checkout(
        self, *, order_reference: str, amount_minor: int, currency: str, idempotency_key: str
    ) -> str: ...
    def verify_webhook(self, body: bytes, headers: dict[str, str]) -> VerifiedPayment: ...
    def refund(self, *, reference: str, amount_minor: int, idempotency_key: str) -> str: ...


def selected_provider() -> PaymentProvider:
    raise ValidationError(
        tr(
            "Paid registration is unavailable until a provider and merchant policy are approved and integrated."
        )
    )
