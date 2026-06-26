"""Per-business resolution picks the right provider/model/key and bot."""

import json
from typing import Any

import httpx

from frontdesk.application.ports import LlmConfig, OutboundMessage, TelegramBotConfig
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.composite import LoggingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.interface.tenancy import provider_from_config, telegram_messaging_from_config

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


async def test_no_config_uses_the_platform_default() -> None:
    sent = await _run(None, _OPENAI_REPLY)

    assert "openrouter.ai" in sent["url"]
    assert sent["headers"]["authorization"] == "Bearer platform-key"
    assert sent["body"]["model"] == "deepseek/deepseek-v4-flash"
    assert sent["body"]["max_tokens"] == 2048


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
