"""Telegram self-serve connect: paste a bot token and the bot goes live.

Validate the token (`getMe`), bind the bot to the business, store it encrypted, and
set up message delivery for the configured transport (ADR-0010):
  - webhook mode: register a webhook (`setWebhook`) at the public URL.
  - polling mode: ensure no webhook (`deleteWebhook`) so the poller's getUpdates works.
Disconnect reverses it. The token is write-only — never returned. See ADR-0008/0009.
"""

import secrets
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from httpx import AsyncClient
from pydantic import BaseModel

from frontdesk.application.ports import (
    ChannelBindingRepository,
    TelegramBotConfig,
    TelegramBotRepository,
)
from frontdesk.core.settings import Settings, TelegramMode
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.channels.telegram import (
    telegram_delete_webhook,
    telegram_get_me,
    telegram_set_webhook,
)


class ConnectInput(BaseModel):
    bot_token: str


class TelegramStatus(BaseModel):
    connected: bool
    username: str | None = None


def build_telegram_connect_router(
    telegram_bots: TelegramBotRepository,
    bindings: ChannelBindingRepository,
    settings: Settings,
    client: AsyncClient,
    guard: Callable[..., Awaitable[None]] | None = None,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])
    base = settings.telegram_api_base
    is_webhook = settings.telegram_mode == TelegramMode.WEBHOOK

    async def register_delivery(token: str, business_id: str, secret: str) -> bool:
        """Set up update delivery for `token`; returns whether a webhook was registered."""
        if is_webhook:
            url = f"{settings.public_url}/webhooks/telegram/{business_id}"
            return await telegram_set_webhook(token, url, secret, client, base)
        await telegram_delete_webhook(token, client, base)  # polling needs no webhook
        return False

    def is_connected(bot: TelegramBotConfig) -> bool:
        # Webhook is connected once registered; polling is connected once the bot is
        # stored (the poller then fetches its updates).
        return bot.webhook_set if is_webhook else True

    @router.post("/api/businesses/{business_id}/telegram/connect")
    async def connect(business_id: str, body: ConnectInput) -> TelegramStatus:
        me = await telegram_get_me(body.bot_token, client, base)
        if me is None:
            raise HTTPException(422, "invalid bot token")
        bid = BusinessId(business_id)
        secret = secrets.token_urlsafe(24)
        await bindings.upsert(Channel.TELEGRAM, me["username"], bid)
        webhook_set = await register_delivery(body.bot_token, business_id, secret)
        bot = TelegramBotConfig(
            bid, body.bot_token, secret, me["username"], webhook_set=webhook_set
        )
        await telegram_bots.upsert(bot)
        return TelegramStatus(connected=is_connected(bot), username=bot.username)

    @router.post("/api/businesses/{business_id}/telegram/disconnect")
    async def disconnect(business_id: str) -> dict[str, bool]:
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is not None:
            await telegram_delete_webhook(bot.bot_token, client, base)
            await bindings.remove(Channel.TELEGRAM, bot.username)
        return {"disconnected": True}

    @router.get("/api/businesses/{business_id}/telegram")
    async def status(business_id: str) -> TelegramStatus:
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is None:
            return TelegramStatus(connected=False)
        return TelegramStatus(connected=is_connected(bot), username=bot.username)

    @router.get("/api/businesses/{business_id}/telegram/health")
    async def health(business_id: str) -> dict[str, object]:
        """Live check: is the stored bot token still valid with Telegram?"""
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is None:
            return {"connected": False, "alive": False}
        me = await telegram_get_me(bot.bot_token, client, base)
        return {"connected": True, "alive": me is not None, "username": bot.username}

    return router
