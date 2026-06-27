"""Run one inbound Telegram message through the right business's assistant.

Shared by both update transports — the webhook (push) and the poller (pull). Applies the
managed-default quota and dispatches to the tenant-wired assistant. While a customer's
message is being handled, a placeholder ("one moment…") is shown and removed when the
real reply lands; a second message from the same customer meanwhile gets a "still on your
previous message" line. See ADR-0010 / ADR-0011.
"""

import logging
from dataclasses import replace

import httpx

from frontdesk.application.assistant import Assistant, AssistantDeps, ai_prefix_for
from frontdesk.application.ports import (
    InboundMessage,
    LlmConfigRepository,
    OutboundMessage,
    Random,
    TelegramBotConfig,
    UsageStore,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.telegram import (
    telegram_delete_message,
    telegram_send_message,
)
from frontdesk.infrastructure.observers import LoggingObserver
from frontdesk.interface.telegram_phrases import BUSY, WAIT
from frontdesk.interface.tenancy import provider_from_config, telegram_messaging_from_config

_logger = logging.getLogger("frontdesk.telegram_inbound")
_QUOTA_MESSAGE = {
    "en": "We've reached today's message limit for the free assistant. "
    "Please try again tomorrow — sorry about that!",
    "es": "Hemos alcanzado el límite de mensajes de hoy del asistente gratuito. "
    "Inténtalo de nuevo mañana — ¡disculpa!",
    "ru": "Достигнут дневной лимит сообщений бесплатного ассистента. "
    "Пожалуйста, попробуйте завтра — извините!",
    "zh": "免费助手今天的消息数量已达上限。请明天再试——抱歉！",
}
_PHRASE_LOCALES = frozenset(WAIT)  # {"en", "es", "ru", "zh"}


class TelegramInbound:
    """Quota, placeholder/busy feedback, and the tenant-wired assistant for one message."""

    def __init__(
        self,
        deps: AssistantDeps,
        llm_configs: LlmConfigRepository,
        usage: UsageStore,
        settings: Settings,
        client: httpx.AsyncClient,
        random: Random,
    ) -> None:
        self._deps = deps
        self._llm_configs = llm_configs
        self._usage = usage
        self._settings = settings
        self._client = client
        self._random = random
        self._base = settings.telegram_api_base
        self._busy: set[str] = set()  # "business:chat" keys currently being handled

    async def handle(self, bot: TelegramBotConfig, inbound: InboundMessage) -> None:
        key = f"{bot.business_id}:{inbound.from_address}"
        locale = await self._locale(bot)
        prefix = ai_prefix_for(locale)  # these filler lines are the AI talking too
        if key in self._busy:
            # A new message arrived while the previous one is still being answered.
            await self._say(bot, inbound.from_address, prefix + self._random.choice(BUSY[locale]))
            return

        self._busy.add(key)
        placeholder_id = await self._say(
            bot, inbound.from_address, prefix + self._random.choice(WAIT[locale])
        )
        try:
            await self._run(bot, inbound, locale)
        finally:
            if placeholder_id is not None:
                await telegram_delete_message(
                    bot.bot_token, inbound.from_address, placeholder_id, self._client, self._base
                )
            self._busy.discard(key)

    async def _say(self, bot: TelegramBotConfig, chat_id: str, text: str) -> int | None:
        return await telegram_send_message(bot.bot_token, chat_id, text, self._client, self._base)

    async def _locale(self, bot: TelegramBotConfig) -> str:
        """The business's chosen language drives the filler phrases; default en."""
        business = await self._deps.businesses.find(bot.business_id)
        code = business.locale if business is not None else "en"
        return code if code in _PHRASE_LOCALES else "en"

    async def _run(self, bot: TelegramBotConfig, inbound: InboundMessage, locale: str) -> None:
        business_id = bot.business_id
        llm_config = await self._llm_configs.get(business_id)
        messaging = telegram_messaging_from_config(bot, self._client, self._base)
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
            quota_text = ai_prefix_for(locale) + _QUOTA_MESSAGE[locale]
            await messaging.send(quota_customer, OutboundMessage(quota_text))
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
