"""Per-business resolution picks the right provider/model/key and bot."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from frontdesk.application.ports import LlmConfig, OutboundMessage, TelegramBotConfig
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.composite import LoggingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.infrastructure.llm_recorder import RecordingLlmProvider
from frontdesk.infrastructure.memory import InMemoryTelegramBotRepository
from frontdesk.interface.tenancy import (
    TenantTelegramMessaging,
    provider_from_config,
    telegram_messaging_from_config,
)

SETTINGS = Settings(
    llm_api_key="platform-key",
    llm_model="deepseek/deepseek-v4-flash",
    llm_base_url="https://openrouter.ai/api/v1",
)


def _capturing_client(captured: dict[str, Any], reply: dict[str, Any]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=reply)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


_OPENAI_REPLY = {"choices": [{"message": {"content": "ok"}}]}
_ANTHROPIC_REPLY = {"content": [{"type": "text", "text": "ok"}]}


async def _run(config: LlmConfig | None, reply: dict[str, Any]) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    client = _capturing_client(captured, reply)
    provider = provider_from_config(config, SETTINGS, client)
    await provider.complete(system="s", messages=[], tools=[])
    return captured


async def _run_channel(
    config: LlmConfig | None, settings: Settings, reply: dict[str, Any], channel: Channel
) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    client = _capturing_client(captured, reply)
    provider = provider_from_config(config, settings, client, channel=channel)
    await provider.complete(system="s", messages=[], tools=[])
    return captured


_VOICE_SETTINGS = Settings(
    llm_api_key="platform-key",
    llm_model="deepseek/deepseek-v4-flash",
    llm_base_url="https://openrouter.ai/api/v1",
    groq_api_key="groq-key",
    voice_llm_model="voice-fast-model",
)


async def test_no_config_uses_the_platform_default() -> None:
    sent = await _run(None, _OPENAI_REPLY)

    assert "openrouter.ai" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer platform-key"
    assert sent["body"]["model"] == "deepseek/deepseek-v4-flash"
    assert sent["body"]["max_tokens"] == 4096  # the settings default budget


async def test_voice_channel_uses_the_groq_fast_tier() -> None:
    sent = await _run_channel(None, _VOICE_SETTINGS, _OPENAI_REPLY, Channel.VOICE)

    assert "api.groq.com" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer groq-key"
    assert sent["body"]["model"] == "voice-fast-model"


async def test_text_channel_keeps_the_default_even_when_voice_tier_configured() -> None:
    sent = await _run_channel(None, _VOICE_SETTINGS, _OPENAI_REPLY, Channel.TELEGRAM)

    assert "openrouter.ai" in sent["url"]
    assert sent["body"]["model"] == "deepseek/deepseek-v4-flash"


async def test_voice_falls_back_to_default_when_groq_unset() -> None:
    # No groq_api_key configured → the per-channel switch is off; voice uses the default provider.
    sent = await _run_channel(None, SETTINGS, _OPENAI_REPLY, Channel.VOICE)

    assert "openrouter.ai" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer platform-key"


async def test_default_mode_uses_the_platform_default() -> None:
    sent = await _run(LlmConfig(BusinessId("b"), "default"), _OPENAI_REPLY)

    assert "openrouter.ai" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer platform-key"


async def test_own_openai_key_and_model() -> None:
    config = LlmConfig(BusinessId("b"), "own", "openai", "gpt-4o", api_key="sk-own")
    sent = await _run(config, _OPENAI_REPLY)

    assert "api.openai.com" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer sk-own"
    assert sent["body"]["model"] == "gpt-4o"


async def test_own_openrouter_key_and_model() -> None:
    config = LlmConfig(BusinessId("b"), "own", "openrouter", "x/y", api_key="sk-or")
    sent = await _run(config, _OPENAI_REPLY)

    assert "openrouter.ai" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer sk-or"
    assert sent["body"]["model"] == "x/y"


async def test_own_anthropic_key_and_model() -> None:
    config = LlmConfig(BusinessId("b"), "own", "anthropic", "claude-x", api_key="sk-ant")
    sent = await _run(config, _ANTHROPIC_REPLY)

    assert "api.anthropic.com/v1/messages" in sent["url"]
    assert sent["headers"]["x-api-key"] == "sk-ant"
    assert sent["body"]["model"] == "claude-x"


def test_messaging_falls_back_to_logging_when_not_connected() -> None:
    assert isinstance(telegram_messaging_from_config(None, httpx.AsyncClient()), LoggingMessaging)


async def test_messaging_uses_the_business_bot_token() -> None:
    captured: dict[str, Any] = {}
    client = _capturing_client(captured, {"ok": True})
    config = TelegramBotConfig(BusinessId("b"), "123:BOTTOKEN", "sec", "ana_bot")

    messaging = telegram_messaging_from_config(config, client)
    assert isinstance(messaging, TelegramMessaging)
    await messaging.send(
        Customer(CustomerId("c"), BusinessId("b"), Channel.TELEGRAM, "555"), OutboundMessage("hi")
    )

    assert "bot123:BOTTOKEN/sendMessage" in captured["url"]  # the business's own token


async def test_tenant_messaging_routes_each_customer_via_its_business_bot() -> None:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    client = _capturing_messaging_client(handler)
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "s1", "ana_bot"))
    await bots.upsert(TelegramBotConfig(BusinessId("biz2"), "222:BBB", "s2", "bob_bot"))
    messaging = TenantTelegramMessaging(bots, client)

    await messaging.send(
        Customer(CustomerId("c1"), BusinessId("biz1"), Channel.TELEGRAM, "11"),
        OutboundMessage("hi"),
    )
    await messaging.send(
        Customer(CustomerId("c2"), BusinessId("biz2"), Channel.TELEGRAM, "22"),
        OutboundMessage("hi"),
    )

    assert any("bot111:AAA/sendMessage" in u for u in sent)
    assert any("bot222:BBB/sendMessage" in u for u in sent)


def _capturing_messaging_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_messaging_honors_a_custom_api_base() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    config = TelegramBotConfig(BusinessId("b"), "123:TOK", "sec", "ana_bot")
    messaging = telegram_messaging_from_config(config, client, "http://mock-telegram:8081")
    await messaging.send(
        Customer(CustomerId("c"), BusinessId("b"), Channel.TELEGRAM, "555"), OutboundMessage("hi")
    )
    assert captured["url"] == "http://mock-telegram:8081/bot123:TOK/sendMessage"  # the override


def test_provider_is_wrapped_to_record_prompts_when_a_log_dir_is_set(tmp_path: Path) -> None:
    settings = Settings(
        llm_api_key="k", llm_model="m", llm_base_url="https://x", llm_log_dir=str(tmp_path)
    )
    provider = provider_from_config(None, settings, httpx.AsyncClient())
    assert isinstance(provider, RecordingLlmProvider)  # recording wrapper around the default


def test_provider_is_not_wrapped_without_a_log_dir() -> None:
    provider = provider_from_config(None, SETTINGS, httpx.AsyncClient())
    assert not isinstance(provider, RecordingLlmProvider)  # the bare default provider


def test_provider_is_not_wrapped_for_a_blank_log_dir() -> None:
    settings = Settings(llm_api_key="k", llm_model="m", llm_base_url="https://x", llm_log_dir="   ")
    provider = provider_from_config(None, settings, httpx.AsyncClient())
    assert not isinstance(provider, RecordingLlmProvider)  # whitespace is treated as "off"
