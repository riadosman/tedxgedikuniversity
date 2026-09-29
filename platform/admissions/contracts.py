"""Validated transport contract; credentials are never coerced or silently truncated."""

from dataclasses import dataclass
import json
from uuid import UUID


@dataclass(frozen=True)
class ScanRequest:
    request_id: UUID
    credential: str = ""
    ticket_id: UUID | None = None
    reason: str = ""
    device: str = ""

    @classmethod
    def parse(cls, body: bytes) -> "ScanRequest":
        if len(body) > 4096:
            raise ValueError("Scan request exceeds the size limit.")
        value: object = json.loads(body)
        if not isinstance(value, dict) or set(value) - {
            "request_id",
            "credential",
            "ticket_id",
            "reason",
            "device",
        }:
            raise ValueError("Invalid scan fields.")

        def text(key: str, maximum: int, default: str = "") -> str:
            item: object = value.get(key, default)
            if not isinstance(item, str) or len(item) > maximum:
                raise ValueError("Invalid scan field type or length.")
            return item

        request_id = UUID(text("request_id", 36))
        raw_ticket: object = value.get("ticket_id")
        ticket_id = UUID(str(raw_ticket)) if isinstance(raw_ticket, str) else None
        if raw_ticket is not None and not isinstance(raw_ticket, str):
            raise ValueError("Invalid ticket identifier.")
        credential = text("credential", 150)
        reason = text("reason", 250)
        if bool(ticket_id) == bool(credential) or (ticket_id and not reason.strip()):
            raise ValueError("Supply one credential or a ticket with a manual admission reason.")
        return cls(request_id, credential, ticket_id, reason, text("device", 80))
