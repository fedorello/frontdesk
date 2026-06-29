"""The owner notification sender routes through the business's own bot (HTML), or skips."""

import json
from collections.abc import Callable

import httpx

from frontdesk.application.ports import TelegramBotConfig
from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.channels.telegram import TelegramOwnerNotificationSender
from frontdesk.infrastructure.memory import InMemoryTelegramBotRepository

BIZ = BusinessId("biz")
Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _bots_with_one() -> InMemoryTelegramBotRepository:
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BIZ, "TOK", "sec", "bot", webhook_set=True))
    return bots


async def test_sends_html_through_the_business_bot() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    sender = TelegramOwnerNotificationSender(await _bots_with_one(), _client(handler))
    await sender.send(BIZ, "owner-chat", "**Hi**")

    assert captured["chat_id"] == "owner-chat"
    assert captured["parse_mode"] == "HTML"
    assert "Hi" in str(captured["text"])
    assert "/botTOK/sendMessage" in str(captured["url"])  # the business's own bot token


async def test_skips_when_no_bot_is_connected() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"ok": True})

    sender = TelegramOwnerNotificationSender(InMemoryTelegramBotRepository(), _client(handler))
    await sender.send(BIZ, "owner-chat", "hi")

    assert called is False  # nothing to send through
