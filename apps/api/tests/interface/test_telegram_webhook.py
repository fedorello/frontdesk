"""The multi-tenant Telegram webhook routes each business to its own bot & model.

A single shared MockTransport plays the LLM (returns a reply) and Telegram
(captures which bot token sent), so we can prove isolation: a message to business 1
is answered by bot 1, a message to business 2 by bot 2.
"""

from datetime import time

import httpx
from fastapi import FastAPI

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import AssistantDeps
from frontdesk.application.ports import TelegramBotConfig
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import Business, Resource, WorkingHours
from frontdesk.infrastructure.memory import (
    AutoDecisionGate,
    InMemoryAppointmentRepository,
    InMemoryBusinessRepository,
    InMemoryCalendar,
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryEventPublisher,
    InMemoryLlmConfigRepository,
    InMemoryMessaging,
    InMemoryReminderStore,
    InMemoryServiceRepository,
    InMemoryTelegramBotRepository,
    InMemoryUsageStore,
    ScriptedLlmProvider,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from frontdesk.interface.telegram_inbound import TelegramInbound
from frontdesk.interface.telegram_webhook import build_telegram_router
from tests.port_contracts import NOW

SETTINGS = Settings(llm_api_key="platform-key", llm_base_url="https://openrouter.ai/api/v1")
UPDATE = {"message": {"message_id": 1, "date": 1782000000, "chat": {"id": 999}, "text": "hi"}}


def _base_deps(businesses: InMemoryBusinessRepository) -> AssistantDeps:
    business = Business(BusinessId("biz1"), "Ana", "UTC")
    resource = Resource(
        ResourceId("res"), BusinessId("biz1"), "Ana", (WorkingHours(0, time(9), time(17)),)
    )
    clock = FixedClock(NOW)
    appointments = InMemoryAppointmentRepository()
    calendar = InMemoryCalendar(
        business, [resource], clock, SequentialIdGenerator("ap"), appointments
    )
    reminders = InMemoryReminderStore()
    scheduler = ReminderScheduler(reminders, SequentialIdGenerator("rem"), clock)
    events = InMemoryEventPublisher()
    return AssistantDeps(
        llm=ScriptedLlmProvider([]),  # replaced per business
        businesses=businesses,
        customers=InMemoryCustomerRepository(SequentialIdGenerator("cus")),
        conversations=InMemoryConversationRepository(),
        services=InMemoryServiceRepository([]),
        appointments=appointments,
        calendar=calendar,
        book=BookAppointment(calendar, scheduler, events),
        reschedule=RescheduleAppointment(calendar, scheduler),
        cancel=CancelAppointment(calendar, reminders, events),
        messaging=InMemoryMessaging(),  # replaced per business
        events=events,
        gate=AutoDecisionGate(approved=False),
        clock=clock,
    )


async def test_routes_each_business_to_its_own_bot() -> None:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "chat/completions" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hello!"}}]})
        if "sendMessage" in url:
            sent.append(url)  # contains bot<token>
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC"), Business(BusinessId("biz2"), "Bob", "UTC")],
        {
            (Channel.TELEGRAM, "ana_bot"): BusinessId("biz1"),
            (Channel.TELEGRAM, "bob_bot"): BusinessId("biz2"),
        },
    )
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec1", "ana_bot"))
    await bots.upsert(TelegramBotConfig(BusinessId("biz2"), "222:BBB", "sec2", "bob_bot"))

    app = FastAPI()
    inbound = TelegramInbound(
        _base_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
    )
    app.include_router(build_telegram_router(inbound, bots))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        ok1 = await web.post(
            "/webhooks/telegram/biz1",
            json=UPDATE,
            headers={"x-telegram-bot-api-secret-token": "sec1"},
        )
        ok2 = await web.post(
            "/webhooks/telegram/biz2",
            json=UPDATE,
            headers={"x-telegram-bot-api-secret-token": "sec2"},
        )
        bad = await web.post(
            "/webhooks/telegram/biz1",
            json=UPDATE,
            headers={"x-telegram-bot-api-secret-token": "WRONG"},
        )
        missing = await web.post(
            "/webhooks/telegram/nope", json=UPDATE, headers={"x-telegram-bot-api-secret-token": "x"}
        )

    assert (ok1.status_code, ok2.status_code, bad.status_code, missing.status_code) == (
        200,
        200,
        403,
        404,
    )
    # Isolation: business 1 replied via bot 111, business 2 via bot 222.
    assert any("bot111:AAA/sendMessage" in u for u in sent)
    assert any("bot222:BBB/sendMessage" in u for u in sent)


async def test_managed_default_daily_limit_caps_messages() -> None:
    llm_calls = 0
    replies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal llm_calls
        url = str(request.url)
        if "chat/completions" in url:
            llm_calls += 1
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hello!"}}]})
        if "sendMessage" in url:
            import json as _json

            replies.append(_json.loads(request.content)["text"])
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz1"), "Ana", "UTC")],
        {(Channel.TELEGRAM, "ana_bot"): BusinessId("biz1")},
    )
    bots = InMemoryTelegramBotRepository()
    await bots.upsert(TelegramBotConfig(BusinessId("biz1"), "111:AAA", "sec1", "ana_bot"))
    settings = Settings(
        llm_api_key="k", llm_base_url="https://openrouter.ai/api/v1", managed_default_daily_limit=1
    )

    app = FastAPI()
    inbound = TelegramInbound(
        _base_deps(businesses),
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        settings,
        client,
    )
    app.include_router(build_telegram_router(inbound, bots))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        headers = {"x-telegram-bot-api-secret-token": "sec1"}
        first = await web.post("/webhooks/telegram/biz1", json=UPDATE, headers=headers)
        second = await web.post("/webhooks/telegram/biz1", json=UPDATE, headers=headers)

    assert (first.status_code, second.status_code) == (200, 200)
    assert llm_calls == 1  # the 2nd message is blocked before reaching the LLM
    assert any("today's message limit" in text for text in replies)  # quota reply sent
