"""Per-business resolution of the LLM provider and the outbound messaging adapter.

Given a business's stored config, build the right adapter — its **own** provider/bot,
or the platform **default**. Pure (config in, adapter out), so it's unit-testable;
the webhook and worker fetch the config from the repositories and call these.
See ADR-0008 / ADR-0009.
"""

from pathlib import Path

import httpx

from frontdesk.application.ports import (
    LlmConfig,
    LlmProvider,
    MessagingPort,
    OutboundMessage,
    TelegramBotConfig,
    TelegramBotRepository,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.composite import LoggingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.infrastructure.llm_recorder import RecordingLlmProvider
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.system import SystemClock

_OPENAI_BASE = "https://api.openai.com/v1"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def provider_from_config(
    config: LlmConfig | None, settings: Settings, client: httpx.AsyncClient
) -> LlmProvider:
    """The business's own provider, or the platform default — wrapped to record prompts if asked."""
    provider = _raw_provider(config, settings, client)
    if settings.llm_log_dir:
        return RecordingLlmProvider(provider, Path(settings.llm_log_dir), SystemClock())
    return provider


def _raw_provider(
    config: LlmConfig | None, settings: Settings, client: httpx.AsyncClient
) -> LlmProvider:
    """The business's own provider, or the platform default when unset/`default`."""
    if config is None or config.mode != "own":
        return OpenAiProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            client=client,
            base_url=settings.llm_base_url,
            max_tokens=settings.llm_max_tokens,
            log_prompts=settings.log_llm_prompts,
        )
    if config.provider == "anthropic":
        return AnthropicProvider(
            api_key=config.api_key or "",
            model=config.model or "",
            client=client,
            max_tokens=settings.llm_max_tokens,
        )
    base_url = config.base_url or (
        _OPENROUTER_BASE if config.provider == "openrouter" else _OPENAI_BASE
    )
    return OpenAiProvider(
        api_key=config.api_key or "",
        model=config.model or "",
        client=client,
        base_url=base_url,
        max_tokens=settings.llm_max_tokens,
        log_prompts=settings.log_llm_prompts,
    )


def telegram_messaging_from_config(
    config: TelegramBotConfig | None,
    client: httpx.AsyncClient,
    base: str = "https://api.telegram.org",
) -> MessagingPort:
    """The business's own Telegram bot, or a logging fallback when not connected."""
    if config is None:
        return LoggingMessaging()
    return TelegramMessaging(
        token=config.bot_token, bot_address=config.username, client=client, base_url=base
    )


class TenantTelegramMessaging:
    """MessagingPort that routes each reply through the customer's business's bot.

    Used by the reminder worker: every reminder is sent from the right business's bot.
    """

    def __init__(
        self,
        telegram_bots: TelegramBotRepository,
        client: httpx.AsyncClient,
        base: str = "https://api.telegram.org",
    ) -> None:
        self._bots = telegram_bots
        self._client = client
        self._base = base

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        bot = await self._bots.get(customer.business_id)
        await telegram_messaging_from_config(bot, self._client, self._base).send(customer, message)
