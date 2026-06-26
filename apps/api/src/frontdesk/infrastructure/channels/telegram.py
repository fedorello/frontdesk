"""Telegram Bot API messaging adapter (outbound) + inbound payload parsing."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from frontdesk.application.ports import InboundMessage, OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.models import Customer


class TelegramMessaging:
    """Sends Telegram messages via the Bot API."""

    def __init__(
        self,
        *,
        token: str,
        bot_address: str,
        client: httpx.AsyncClient,
        base_url: str = "https://api.telegram.org",
    ) -> None:
        self._token = token
        self._bot_address = bot_address  # the bot's own address (tenant binding)
        self._client = client
        self._base = base_url.rstrip("/")

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        payload: dict[str, object] = {"chat_id": customer.channel_address, "text": message.text}
        if message.buttons:
            payload["reply_markup"] = {
                "keyboard": [[{"text": button} for button in message.buttons]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        response = await self._client.post(
            f"{self._base}/bot{self._token}/sendMessage", json=payload
        )
        response.raise_for_status()


def parse_telegram_inbound(
    payload: Mapping[str, Any], *, bot_address: str
) -> InboundMessage | None:
    """Normalize a Telegram update to an InboundMessage, or None for non-text updates."""
    try:
        message = payload["message"]
        return InboundMessage(
            channel=Channel.TELEGRAM,
            from_address=str(message["chat"]["id"]),
            to_address=bot_address,
            text=message["text"],
            received_at=datetime.fromtimestamp(int(message["date"]), tz=UTC),
            provider_message_id=f"{message['chat']['id']}:{message['message_id']}",
        )
    except KeyError, TypeError:
        return None


_TELEGRAM_API = "https://api.telegram.org"


async def telegram_get_me(token: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Validate a bot token: returns the bot info (incl. username), or None if invalid."""
    response = await client.get(f"{_TELEGRAM_API}/bot{token}/getMe")
    data = response.json()
    return data["result"] if data.get("ok") else None


async def telegram_set_webhook(
    token: str, url: str, secret: str, client: httpx.AsyncClient
) -> bool:
    response = await client.post(
        f"{_TELEGRAM_API}/bot{token}/setWebhook", json={"url": url, "secret_token": secret}
    )
    return bool(response.json().get("ok"))


async def telegram_delete_webhook(token: str, client: httpx.AsyncClient) -> bool:
    response = await client.post(f"{_TELEGRAM_API}/bot{token}/deleteWebhook")
    return bool(response.json().get("ok"))
