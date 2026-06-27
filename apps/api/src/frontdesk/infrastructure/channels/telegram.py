"""Telegram Bot API messaging adapter (outbound) + inbound payload parsing."""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from frontdesk.application.ports import (
    InboundMessage,
    OutboundMessage,
    TelegramBotRepository,
)
from frontdesk.domain.enums import Channel
from frontdesk.domain.models import Business, Customer
from frontdesk.infrastructure.channels.telegram_format import markdown_to_telegram_html

_logger = logging.getLogger("frontdesk.telegram")


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
        payload: dict[str, object] = {
            "chat_id": customer.channel_address,
            "text": markdown_to_telegram_html(message.text),
            "parse_mode": "HTML",
        }
        if message.buttons:
            payload["reply_markup"] = {
                "keyboard": [[{"text": button} for button in message.buttons]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        url = f"{self._base}/bot{self._token}/sendMessage"
        response = await self._client.post(url, json=payload)
        if response.status_code == httpx.codes.BAD_REQUEST:
            # Malformed HTML entities — resend as plain text so the reply still arrives.
            payload["text"] = message.text
            del payload["parse_mode"]
            response = await self._client.post(url, json=payload)
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


async def telegram_get_me(
    token: str, client: httpx.AsyncClient, base: str = _TELEGRAM_API
) -> dict[str, Any] | None:
    """Validate a bot token: returns the bot info (incl. username), or None.

    Returns None for an invalid token *or* an unreachable Telegram — connect treats
    both as "couldn't validate" rather than crashing the request.
    """
    try:
        response = await client.get(f"{base.rstrip('/')}/bot{token}/getMe")
        data = response.json()
    except httpx.HTTPError as exc:
        _logger.warning("telegram getMe failed: %s", exc)
        return None
    return data["result"] if data.get("ok") else None


async def telegram_set_webhook(
    token: str, url: str, secret: str, client: httpx.AsyncClient, base: str = _TELEGRAM_API
) -> bool:
    try:
        response = await client.post(
            f"{base.rstrip('/')}/bot{token}/setWebhook", json={"url": url, "secret_token": secret}
        )
        return bool(response.json().get("ok"))
    except httpx.HTTPError as exc:
        _logger.warning("telegram setWebhook failed: %s", exc)
        return False


async def telegram_delete_webhook(
    token: str, client: httpx.AsyncClient, base: str = _TELEGRAM_API
) -> bool:
    try:
        response = await client.post(f"{base.rstrip('/')}/bot{token}/deleteWebhook")
        return bool(response.json().get("ok"))
    except httpx.HTTPError as exc:
        _logger.warning("telegram deleteWebhook failed: %s", exc)
        return False


async def telegram_get_updates(
    token: str,
    client: httpx.AsyncClient,
    *,
    offset: int,
    timeout: int,
    base: str = _TELEGRAM_API,
) -> list[dict[str, Any]]:
    """Long-poll for message updates after `offset`; returns [] on any error.

    `timeout` is Telegram's long-poll hold time in seconds — the HTTP client timeout
    must exceed it. Only `message` updates are requested.
    """
    try:
        response = await client.get(
            f"{base.rstrip('/')}/bot{token}/getUpdates",
            params={"offset": offset, "timeout": timeout, "allowed_updates": '["message"]'},
        )
        data = response.json()
    except httpx.HTTPError as exc:
        _logger.warning("telegram getUpdates failed: %s", exc)
        return []
    return list(data["result"]) if data.get("ok") else []


class TelegramCustomerNotifier:
    """Sends a one-off message to a customer over their business's own Telegram bot."""

    def __init__(
        self, bots: TelegramBotRepository, client: httpx.AsyncClient, base: str = _TELEGRAM_API
    ) -> None:
        self._bots = bots
        self._client = client
        self._base = base

    async def notify(self, business: Business, customer: Customer, text: str) -> None:
        bot = await self._bots.get(business.id)
        if bot is None:
            _logger.warning("no telegram bot for business %s; cannot notify", business.id)
            return
        await telegram_send_message(
            bot.bot_token, customer.channel_address, text, self._client, self._base
        )


async def telegram_send_message(
    token: str, chat_id: str, text: str, client: httpx.AsyncClient, base: str = _TELEGRAM_API
) -> int | None:
    """Send a plain text message; return its message_id (to delete it later), or None."""
    try:
        response = await client.post(
            f"{base.rstrip('/')}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        data = response.json()
    except httpx.HTTPError as exc:
        _logger.warning("telegram sendMessage failed: %s", exc)
        return None
    message_id = data.get("result", {}).get("message_id") if data.get("ok") else None
    return int(message_id) if message_id is not None else None


async def telegram_delete_message(
    token: str, chat_id: str, message_id: int, client: httpx.AsyncClient, base: str = _TELEGRAM_API
) -> None:
    """Delete a previously sent message (best-effort; a failure is logged, not raised)."""
    try:
        await client.post(
            f"{base.rstrip('/')}/bot{token}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        )
    except httpx.HTTPError as exc:
        _logger.warning("telegram deleteMessage failed: %s", exc)
