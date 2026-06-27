"""The polling transport: concurrent dispatch, offset, placeholder, and busy feedback."""

import asyncio
import json
from datetime import UTC, datetime

import httpx

from frontdesk.application.ports import InboundMessage, TelegramBotConfig, TelegramBotRepository
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId
from frontdesk.domain.models import Business
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryLlmConfigRepository,
    InMemoryTelegramBotRepository,
    InMemoryUsageStore,
)
from frontdesk.infrastructure.system import FixedRandom
from frontdesk.interface.telegram_inbound import TelegramInbound
from frontdesk.interface.telegram_phrases import BUSY, WAIT
from frontdesk.interface.telegram_poller import TelegramPoller
from tests.assistant_deps import build_assistant_deps

SETTINGS = Settings(llm_api_key="platform-key", llm_base_url="https://openrouter.ai/api/v1")
ONE_UPDATE = {
    "update_id": 100,
    "message": {"message_id": 1, "date": 1782000000, "chat": {"id": 555}, "text": "hi"},
}


def _businesses() -> InMemoryBusinessRepository:
    return InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )


def _inbound(businesses: InMemoryBusinessRepository, client: httpx.AsyncClient) -> TelegramInbound:
    return TelegramInbound(
        build_assistant_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
        FixedRandom(),
    )


async def _connected_bot(bots: TelegramBotRepository) -> TelegramBotConfig:
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot"))
    bot = await bots.get(BusinessId("biz1"))
    assert bot is not None
    return bot


async def _drain(poller: TelegramPoller) -> None:
    """Wait for the poller's in-flight dispatch tasks to finish."""
    if poller._tasks:
        await asyncio.gather(*poller._tasks)


async def test_poll_dispatches_a_message_and_advances_the_offset() -> None:
    sent: list[str] = []
    update_offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "getUpdates" in url:
            update_offsets.append(url)
            return httpx.Response(200, json={"ok": True, "result": [ONE_UPDATE]})
        if "chat/completions" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hello!"}}]})
        if "sendMessage" in url:
            sent.append(json.loads(request.content)["text"])
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
        if "deleteMessage" in url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = _businesses()
    bots = InMemoryTelegramBotRepository()
    bot = await _connected_bot(bots)
    poller = TelegramPoller(bots, _inbound(businesses, client), client, SETTINGS)

    await poller._poll_bot(bot)
    await _drain(poller)

    assert any(WAIT["en"][0] in m for m in sent)  # a placeholder was shown first
    assert any("Hello!" in m for m in sent)  # then the real reply (under the AI prefix)
    after = await bots.get(BusinessId("biz1"))
    assert after is not None
    assert after.last_update_id == 100  # cursor advanced past the handled update
    assert any("offset=1" in url for url in update_offsets)  # first poll used offset last+1


async def test_poll_advances_offset_even_when_dispatch_fails() -> None:
    # A poison update (sendMessage fails) must not wedge the loop — the offset still advances.
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "getUpdates" in url:
            return httpx.Response(200, json={"ok": True, "result": [ONE_UPDATE]})
        if "chat/completions" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hi"}}]})
        if "sendMessage" in url:
            return httpx.Response(500, json={"ok": False})  # outbound fails
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    bots = InMemoryTelegramBotRepository()
    bot = await _connected_bot(bots)
    poller = TelegramPoller(bots, _inbound(_businesses(), client), client, SETTINGS)

    await poller._poll_bot(bot)
    await _drain(poller)

    after = await bots.get(BusinessId("biz1"))
    assert after is not None
    assert after.last_update_id == 100  # advanced despite the failure


async def test_run_polls_until_stopped() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        url = str(request.url)
        if "getUpdates" in url:
            calls += 1
            return httpx.Response(
                200, json={"ok": True, "result": [ONE_UPDATE] if calls == 1 else []}
            )
        if "chat/completions" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hi"}}]})
        if "sendMessage" in url:
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
        if "deleteMessage" in url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    bots = InMemoryTelegramBotRepository()
    await _connected_bot(bots)
    poller = TelegramPoller(bots, _inbound(_businesses(), client), client, SETTINGS)

    stop = asyncio.Event()
    task = asyncio.create_task(poller.run(stop))
    for _ in range(200):
        await asyncio.sleep(0.01)
        bot = await bots.get(BusinessId("biz1"))
        if bot is not None and bot.last_update_id == 100:
            break
    stop.set()
    await asyncio.wait_for(task, timeout=2)

    after = await bots.get(BusinessId("biz1"))
    assert after is not None
    assert after.last_update_id == 100  # the running loop dispatched the update


async def test_run_idles_when_no_bots_are_connected() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    settings = Settings(telegram_idle_poll_seconds=0)  # don't slow the test
    poller = TelegramPoller(
        InMemoryTelegramBotRepository(),
        TelegramInbound(
            build_assistant_deps(InMemoryBusinessRepository([], {})),
            InMemoryLlmConfigRepository(),
            InMemoryUsageStore(),
            settings,
            client,
            FixedRandom(),
        ),
        client,
        settings,
    )

    stop = asyncio.Event()
    task = asyncio.create_task(poller.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=2)  # exits cleanly with nothing to poll


class _FlakyBots:
    """A bot repo whose first list_connected fails (e.g. Postgres recovering), then recovers."""

    def __init__(self) -> None:
        self._inner = InMemoryTelegramBotRepository()
        self.calls = 0

    async def list_connected(self) -> list[TelegramBotConfig]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("the database system is in recovery mode")
        return await self._inner.list_connected()

    async def get(self, business_id: BusinessId) -> TelegramBotConfig | None:
        return await self._inner.get(business_id)

    async def upsert(self, config: TelegramBotConfig) -> None:
        await self._inner.upsert(config)

    async def set_offset(self, business_id: BusinessId, last_update_id: int) -> None:
        await self._inner.set_offset(business_id, last_update_id)


async def test_run_survives_a_transient_repo_error() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    settings = Settings(telegram_idle_poll_seconds=0)
    bots = _FlakyBots()
    poller = TelegramPoller(
        bots,
        TelegramInbound(
            build_assistant_deps(InMemoryBusinessRepository([], {})),
            InMemoryLlmConfigRepository(),
            InMemoryUsageStore(),
            settings,
            client,
            FixedRandom(),
        ),
        client,
        settings,
    )

    stop = asyncio.Event()
    task = asyncio.create_task(poller.run(stop))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if bots.calls >= 2:  # got past the failing first round
            break
    stop.set()
    await asyncio.wait_for(task, timeout=2)

    assert bots.calls >= 2  # the loop did not die on the first error


class _BlockingLlm(httpx.AsyncBaseTransport):
    """Holds the LLM call open until `release` is set, so a message stays mid-flight."""

    def __init__(self, release: asyncio.Event, sent: list[str]) -> None:
        self._release = release
        self._sent = sent

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "chat/completions" in url:
            await self._release.wait()
            return httpx.Response(200, json={"choices": [{"message": {"content": "done"}}]})
        if "sendMessage" in url:
            self._sent.append(json.loads(request.content)["text"])
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
        if "deleteMessage" in url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)


async def test_second_message_while_busy_gets_the_busy_phrase() -> None:
    release = asyncio.Event()
    sent: list[str] = []
    client = httpx.AsyncClient(transport=_BlockingLlm(release, sent))
    inbound = _inbound(_businesses(), client)
    bot = TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot")
    when = datetime(2026, 6, 26, tzinfo=UTC)
    first = InboundMessage(Channel.TELEGRAM, "555", "ana_bot", "first", when, "555:1")
    second = InboundMessage(Channel.TELEGRAM, "555", "ana_bot", "second", when, "555:2")

    task1 = asyncio.create_task(inbound.handle(bot, first))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if sent:  # the placeholder is out → the first message is in flight (busy)
            break
    await inbound.handle(bot, second)  # arrives while the first is still being answered
    release.set()
    await asyncio.wait_for(task1, timeout=2)

    assert any(WAIT["en"][0] in m for m in sent)  # the first got a placeholder
    assert any(BUSY["en"][0] in m for m in sent)  # the second got the busy line


async def test_placeholder_uses_the_business_locale() -> None:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "chat/completions" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "ответ"}}]})
        if "sendMessage" in url:
            sent.append(json.loads(request.content)["text"])
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
        if "deleteMessage" in url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC", locale="ru")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )
    inbound = _inbound(businesses, client)
    bot = TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot")
    when = datetime(2026, 6, 26, tzinfo=UTC)
    message = InboundMessage(Channel.TELEGRAM, "555", "ana_bot", "привет", when, "555:1")

    await inbound.handle(bot, message)

    assert any(
        WAIT["ru"][0] in m for m in sent
    )  # the filler phrase follows the business's chosen language
