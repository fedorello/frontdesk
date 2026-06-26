"""Telegram self-serve connect (M3): paste a bot token and the bot goes live.

Validate the token (`getMe`), store it encrypted, bind the bot to the business, and
register the webhook (`setWebhook` with a per-business secret). Disconnect reverses
it. The token is write-only — never returned. See ADR-0008 / ADR-0009.
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
from frontdesk.core.settings import Settings
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

    @router.post("/api/businesses/{business_id}/telegram/connect")
    async def connect(business_id: str, body: ConnectInput) -> TelegramStatus:
        me = await telegram_get_me(body.bot_token, client)
        if me is None:
            raise HTTPException(422, "invalid bot token")
        username = me["username"]
        bid = BusinessId(business_id)
        secret = secrets.token_urlsafe(24)

        await bindings.upsert(Channel.TELEGRAM, username, bid)
        webhook_url = f"{settings.public_url}/webhooks/telegram/{business_id}"
        registered = await telegram_set_webhook(body.bot_token, webhook_url, secret, client)
        await telegram_bots.upsert(
            TelegramBotConfig(bid, body.bot_token, secret, username, webhook_set=registered)
        )
        return TelegramStatus(connected=registered, username=username)

    @router.post("/api/businesses/{business_id}/telegram/disconnect")
    async def disconnect(business_id: str) -> dict[str, bool]:
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is not None:
            await telegram_delete_webhook(bot.bot_token, client)
            await bindings.remove(Channel.TELEGRAM, bot.username)
        return {"disconnected": True}

    @router.get("/api/businesses/{business_id}/telegram")
    async def status(business_id: str) -> TelegramStatus:
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is None:
            return TelegramStatus(connected=False)
        return TelegramStatus(connected=bot.webhook_set, username=bot.username)

    return router
