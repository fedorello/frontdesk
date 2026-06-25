"""WhatsApp Cloud API messaging adapter (outbound) + inbound payload parsing."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from frontdesk.application.ports import InboundMessage, OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.models import Customer

_MAX_BUTTONS = 3  # WhatsApp interactive reply-button limit


class WhatsAppMessaging:
    """Sends WhatsApp messages via the Meta Cloud API (Graph API)."""

    def __init__(
        self,
        *,
        token: str,
        phone_number_id: str,
        client: httpx.AsyncClient,
        base_url: str = "https://graph.facebook.com/v21.0",
    ) -> None:
        self._token = token
        self._phone_number_id = phone_number_id
        self._client = client
        self._base = base_url.rstrip("/")

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        payload: dict[str, object] = {
            "messaging_product": "whatsapp",
            "to": customer.channel_address,
        }
        if message.buttons:
            payload["type"] = "interactive"
            payload["interactive"] = {
                "type": "button",
                "body": {"text": message.text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": button, "title": button}}
                        for button in message.buttons[:_MAX_BUTTONS]
                    ]
                },
            }
        else:
            payload["type"] = "text"
            payload["text"] = {"body": message.text}
        response = await self._client.post(
            f"{self._base}/{self._phone_number_id}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        response.raise_for_status()


def parse_whatsapp_inbound(payload: Mapping[str, Any]) -> InboundMessage | None:
    """Normalize a WhatsApp webhook payload to an InboundMessage, or None.

    Returns None for non-message events (statuses, read receipts, …).
    """
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        return InboundMessage(
            channel=Channel.WHATSAPP,
            from_address=message["from"],
            to_address=value["metadata"]["display_phone_number"],
            text=message["text"]["body"],
            received_at=datetime.fromtimestamp(int(message["timestamp"]), tz=UTC),
            provider_message_id=message["id"],
        )
    except KeyError, IndexError, TypeError:
        return None
