"""Live behavioral eval: run real conversations against a hosted model.

Run locally (needs a real key); not part of CI. Mirrors the deterministic evals
in tests/evals but against an actual LLM.

    FD_LLM_KEY=sk-or-... FD_LLM_MODEL=deepseek/deepseek-v4-flash \
        uv run python scripts/eval_live.py
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, time

import httpx

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import InboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, ResourceId, ServiceId
from frontdesk.domain.models import Business, KnowledgeItem, Resource, Service, WorkingHours
from frontdesk.infrastructure.memory import (
    AutoDecisionGate,
    InMemoryAppointmentRepository,
    InMemoryBusinessRepository,
    InMemoryCalendar,
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryEventPublisher,
    InMemoryMessaging,
    InMemoryReminderStore,
    InMemoryServiceRepository,
)
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def build(provider):
    biz = Business(
        BusinessId("biz"),
        "Ana's Studio",
        "UTC",
        lead_time_minutes=0,
        buffer_minutes=15,
        knowledge=(KnowledgeItem("opening hours", "We're open 9 to 17, Monday to Friday."),),
    )
    res = Resource(
        ResourceId("res"),
        BusinessId("biz"),
        "Ana",
        tuple(WorkingHours(d, time(9), time(17)) for d in range(7)),
    )
    svc = Service(ServiceId("svc"), BusinessId("biz"), "Haircut", 60, resource_ids=(ResourceId("res"),))
    clock = FixedClock(NOW)
    appts = InMemoryAppointmentRepository()
    cal = InMemoryCalendar(biz, [res], clock, SequentialIdGenerator("ap"), appts)
    rem = InMemoryReminderStore()
    ev = InMemoryEventPublisher()
    msg = InMemoryMessaging()
    deps = AssistantDeps(
        provider,
        InMemoryBusinessRepository([biz], {(Channel.WHATSAPP, "+BIZ"): biz.id}),
        InMemoryCustomerRepository(SequentialIdGenerator("cus")),
        InMemoryConversationRepository(),
        InMemoryServiceRepository([svc]),
        appts,
        cal,
        BookAppointment(cal, ReminderScheduler(rem, SequentialIdGenerator("rem"), clock), ev),
        RescheduleAppointment(cal, ReminderScheduler(rem, SequentialIdGenerator("rm"), clock)),
        CancelAppointment(cal, rem, ev),
        msg,
        ev,
        AutoDecisionGate(approved=False),
        clock,
    )
    return Assistant(deps), msg, appts


async def main():
    key = os.environ["FD_LLM_KEY"]
    model = os.environ.get("FD_LLM_MODEL", "deepseek/deepseek-v4-flash")
    print(f"model: {model}\n")
    passed = 0
    failed = 0
    async with httpx.AsyncClient(timeout=60) as client:
        provider = OpenAiProvider(
            api_key=key, model=model, client=client, base_url="https://openrouter.ai/api/v1"
        )

        # 1) Books the slot the customer asks for.
        assistant, msg, appts = build(provider)
        await assistant.handle(
            InboundMessage(
                Channel.WHATSAPP,
                "+591",
                "+BIZ",
                "I'd like a Haircut today at 12:30. Check what's free and book it for me.",
                NOW,
                "e1",
            )
        )
        booked = any(
            (ap.slot.starts_at.hour, ap.slot.starts_at.minute) == (12, 30)
            for ap in appts.appointments.values()
        )
        reply = msg.sent[-1][1].text if msg.sent else "(no reply)"
        print(f"[{'PASS' if booked else 'FAIL'}] books an offered 12:30 haircut -> {reply[:60]!r}")
        passed, failed = (passed + booked, failed + (not booked))

        # 2) Answers opening hours from the knowledge base (no invention).
        # The model may relay "9 to 17" as "9 AM to 5 PM" — both are grounded.
        assistant, msg, appts = build(provider)
        await assistant.handle(
            InboundMessage(Channel.WHATSAPP, "+592", "+BIZ", "what are your opening hours?", NOW, "e2")
        )
        reply = msg.sent[-1][1].text if msg.sent else ""
        grounded = "9" in reply and ("17" in reply or "5" in reply)
        print(f"[{'PASS' if grounded else 'FAIL'}] grounds opening hours -> {reply[:70]!r}")
        passed, failed = (passed + grounded, failed + (not grounded))

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


asyncio.run(main())
