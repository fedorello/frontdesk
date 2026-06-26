"""The polling transport: long-poll getUpdates, dispatch to the assistant, advance offset."""

import json

import httpx

from frontdesk.application.ports import TelegramBotConfig
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
from frontdesk.interface.telegram_inbound import TelegramInbound
from frontdesk.interface.telegram_poller import TelegramPoller
from tests.assistant_deps import build_assistant_deps

SETTINGS = Settings(llm_api_key="platform-key", llm_base_url="https://openrouter.ai/api/v1")
ONE_UPDATE = {
    "update_id": 100,
    "message": {"message_id": 1, "date": 1782000000, "chat": {"id": 555}, "text": "hi"},
}


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
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot"))
    inbound = TelegramInbound(
        build_assistant_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
    )
    poller = TelegramPoller(bots, inbound, client, SETTINGS)

    bot = await bots.get(BusinessId("biz1"))
    assert bot is not None
    await poller._poll_bot(bot)

    assert sent == ["Hello!"]  # the assistant replied via the bot
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
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot"))
    inbound = TelegramInbound(
        build_assistant_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
    )
    poller = TelegramPoller(bots, inbound, client, SETTINGS)

    bot = await bots.get(BusinessId("biz1"))
    assert bot is not None
    await poller._poll_bot(bot)

    after = await bots.get(BusinessId("biz1"))
    assert after is not None
    assert after.last_update_id == 100  # advanced despite the failure


async def test_run_polls_until_stopped() -> None:
    import asyncio

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
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec", "ana_bot"))
    inbound = TelegramInbound(
        build_assistant_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
    )
    poller = TelegramPoller(bots, inbound, client, SETTINGS)

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
    import asyncio

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
        ),
        client,
        settings,
    )

    stop = asyncio.Event()
    task = asyncio.create_task(poller.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=2)  # exits cleanly with nothing to poll
