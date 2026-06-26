"""The multi-tenant Telegram webhook: one path per business, its own bot & model.

`POST /webhooks/telegram/{business}` resolves the business from the path, verifies
its own secret token, and dispatches to the assistant wired with **that business's**
bot (for the reply) and LLM provider. Businesses on the managed-default LLM are
capped at a daily message quota (cost control). See ADR-0008 / ADR-0009.
"""

import json
import logging
from dataclasses import replace

import httpx
from fastapi import APIRouter, Request, Response

from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import (
    LlmConfigRepository,
    OutboundMessage,
    TelegramBotRepository,
    UsageStore,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.telegram import parse_telegram_inbound
from frontdesk.infrastructure.observers import LoggingObserver
from frontdesk.interface.tenancy import provider_from_config, telegram_messaging_from_config

_SECRET_HEADER = "x-telegram-bot-api-secret-token"
_logger = logging.getLogger("frontdesk.webhook")
_QUOTA_MESSAGE = (
    "We've reached today's message limit for the free assistant. "
    "Please try again tomorrow — sorry about that!"
)


def build_telegram_router(
    deps: AssistantDeps,
    telegram_bots: TelegramBotRepository,
    llm_configs: LlmConfigRepository,
    usage: UsageStore,
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
        if inbound is None:
            return Response(status_code=200)

        llm_config = await llm_configs.get(bid)
        messaging = telegram_messaging_from_config(bot, client)
        on_managed_default = llm_config is None or llm_config.mode != "own"
        _logger.info(
            "inbound business=%s from=%s mode=%s text=%r",
            business_id,
            inbound.from_address,
            "default" if on_managed_default else "own",
            inbound.text,
        )
        limit = settings.managed_default_daily_limit
        if on_managed_default and limit > 0:
            day = deps.clock.now().date().isoformat()
            count = await usage.increment_and_count(bid, day)
            if count > limit:
                _logger.warning(
                    "quota_exceeded business=%s count=%s limit=%s", business_id, count, limit
                )
                customer = Customer(CustomerId("quota"), bid, inbound.channel, inbound.from_address)
                await messaging.send(customer, OutboundMessage(_QUOTA_MESSAGE))
                return Response(status_code=200)

        assistant = Assistant(
            replace(
                deps,
                messaging=messaging,
                llm=provider_from_config(llm_config, settings, client),
            ),
            LoggingObserver(business_id),
        )
        await assistant.handle(inbound)
        _logger.info("handled business=%s from=%s", business_id, inbound.from_address)
        return Response(status_code=200)

    return router
