"""The multi-tenant Telegram webhook (push transport): one path per business.

`POST /webhooks/telegram/{business}` resolves the business from the path, verifies its
own secret token, and hands a parsed update to the shared TelegramInbound dispatcher.
Used when telegram_mode == "webhook" (a public URL is available). See ADR-0010.
"""

import json

from fastapi import APIRouter, Request, Response

from frontdesk.application.ports import TelegramBotRepository
from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.channels.telegram import parse_telegram_inbound
from frontdesk.interface.telegram_inbound import TelegramInbound

_SECRET_HEADER = "x-telegram-bot-api-secret-token"


def build_telegram_router(
    inbound: TelegramInbound,
    telegram_bots: TelegramBotRepository,
) -> APIRouter:
    router = APIRouter()

    @router.post("/webhooks/telegram/{business_id}")
    async def telegram(business_id: str, request: Request) -> Response:
        bot = await telegram_bots.get(BusinessId(business_id))
        if bot is None:
            return Response(status_code=404)
        if request.headers.get(_SECRET_HEADER) != bot.secret_token:
            return Response(status_code=403)

        message = parse_telegram_inbound(json.loads(await request.body()), bot_address=bot.username)
        if message is not None:
            await inbound.handle(bot, message)
        return Response(status_code=200)

    return router
