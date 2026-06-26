"""Run one inbound Telegram message through the right business's assistant.

Shared by both update transports — the webhook (push) and the poller (pull). Each
resolves a known bot and a parsed InboundMessage; this applies the managed-default
quota and dispatches to the tenant-wired assistant. See ADR-0010.
"""

import logging
from dataclasses import replace

import httpx

from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import (
    InboundMessage,
    LlmConfigRepository,
    OutboundMessage,
    TelegramBotConfig,
    UsageStore,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.observers import LoggingObserver
from frontdesk.interface.tenancy import provider_from_config, telegram_messaging_from_config

_logger = logging.getLogger("frontdesk.telegram_inbound")
_QUOTA_MESSAGE = (
    "We've reached today's message limit for the free assistant. "
    "Please try again tomorrow — sorry about that!"
)


class TelegramInbound:
    """Applies the per-business quota and runs the assistant wired with that bot + model."""

    def __init__(
        self,
        deps: AssistantDeps,
        llm_configs: LlmConfigRepository,
        usage: UsageStore,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> None:
        self._deps = deps
        self._llm_configs = llm_configs
        self._usage = usage
        self._settings = settings
        self._client = client

    async def handle(self, bot: TelegramBotConfig, inbound: InboundMessage) -> None:
        business_id = bot.business_id
        llm_config = await self._llm_configs.get(business_id)
        messaging = telegram_messaging_from_config(
            bot, self._client, self._settings.telegram_api_base
        )
        on_managed_default = llm_config is None or llm_config.mode != "own"
        _logger.info(
            "inbound business=%s from=%s mode=%s text=%r",
            business_id,
            inbound.from_address,
            "default" if on_managed_default else "own",
            inbound.text,
        )

        if on_managed_default and await self._over_quota(business_id):
            quota_customer = Customer(
                CustomerId("quota"), business_id, inbound.channel, inbound.from_address
            )
            await messaging.send(quota_customer, OutboundMessage(_QUOTA_MESSAGE))
            return

        assistant = Assistant(
            replace(
                self._deps,
                messaging=messaging,
                llm=provider_from_config(llm_config, self._settings, self._client),
            ),
            LoggingObserver(str(business_id)),
        )
        await assistant.handle(inbound)
        _logger.info("handled business=%s from=%s", business_id, inbound.from_address)

    async def _over_quota(self, business_id: BusinessId) -> bool:
        limit = self._settings.managed_default_daily_limit
        if limit <= 0:
            return False
        day = self._deps.clock.now().date().isoformat()
        count = await self._usage.increment_and_count(business_id, day)
        if count > limit:
            _logger.warning(
                "quota_exceeded business=%s count=%s limit=%s", business_id, count, limit
            )
            return True
        return False
