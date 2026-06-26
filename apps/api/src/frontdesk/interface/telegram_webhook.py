"""The multi-tenant Telegram webhook: one path per business, its own bot & model.

`POST /webhooks/telegram/{business}` resolves the business from the path, verifies
its own secret token, and dispatches to the assistant wired with **that business's**
bot (for the reply) and LLM provider. See ADR-0008 / ADR-0009.
"""

import json
from dataclasses import replace

import httpx
from fastapi import APIRouter, Request, Response

from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import LlmConfigRepository, TelegramBotRepository
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.channels.telegram import parse_telegram_inbound
from frontdesk.interface.tenancy import provider_from_config, telegram_messaging_from_config

_SECRET_HEADER = "x-telegram-bot-api-secret-token"


def build_telegram_router(
    deps: AssistantDeps,
    telegram_bots: TelegramBotRepository,
    llm_configs: LlmConfigRepository,
    settings: Settings,
    client: httpx.AsyncClient,
) -> APIRouter:
    router = APIRouter()

    @router.post("/webhooks/telegram/{business_id}")
    async def telegram(business_id: str, request: Request) -> Response:
        bid = BusinessId(business_id)
        bot = await telegram_bots.get(bid)
        if bot is None:
            return Response(status_code=404)
        if request.headers.get(_SECRET_HEADER) != bot.secret_token:
            return Response(status_code=403)

        inbound = parse_telegram_inbound(json.loads(await request.body()), bot_address=bot.username)
        if inbound is not None:
            llm_config = await llm_configs.get(bid)
            assistant = Assistant(
                replace(
                    deps,
                    messaging=telegram_messaging_from_config(bot, client),
                    llm=provider_from_config(llm_config, settings, client),
                )
            )
            await assistant.handle(inbound)
        return Response(status_code=200)

    return router
