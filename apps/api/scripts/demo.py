"""One-command demo: the whole product, locally, against real Postgres + a real model.

    make up                 # Postgres + Redis
    FD_LLM_KEY=sk-or-... uv run python scripts/demo.py

Seeds a demo business, then a WhatsApp-style message drives the real assistant
(SQL-backed) to book an appointment — persisted in Postgres.
"""

import asyncio
import json
import os
from datetime import UTC, datetime, time

import httpx
from sqlalchemy import text

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import InboundMessage
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.memory import AutoDecisionGate
from frontdesk.infrastructure.postgres.adapters import (
    SqlAppointmentRepository,
    SqlBusinessRepository,
    SqlCalendar,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlReminderStore,
    SqlServiceRepository,
)
from frontdesk.infrastructure.postgres.schema import CREATE_STATEMENTS, DROP_STATEMENTS
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.system import FixedClock, UuidIdGenerator

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
HOURS = json.dumps([{"weekday": d, "opens": "09:00:00", "closes": "17:00:00"} for d in range(7)])
KNOWLEDGE = json.dumps([{"question": "opening hours", "answer": "We're open 9 to 17, Mon-Fri."}])


class ConsoleMessaging:
    async def send(self, customer, message) -> None:
        print(f"   🤖  → {customer.channel_address}: {message.text}")


class ConsoleEvents:
    async def publish(self, event) -> None:
        print(f"   ·   {type(event).__name__}")


async def seed(sf) -> None:
    async with sf() as session:
        for statement in DROP_STATEMENTS:
            await session.execute(text(statement))
        for statement in CREATE_STATEMENTS:
            await session.execute(text(statement))
        await session.execute(
            text(
                "INSERT INTO business (id, name, timezone, knowledge) "
                "VALUES ('ana', 'Ana''s Studio', 'UTC', CAST(:kb AS jsonb))"
            ),
            {"kb": KNOWLEDGE},
        )
        await session.execute(
            text(
                "INSERT INTO channel_binding (channel, address, business_id) "
                "VALUES ('whatsapp', '+BIZ', 'ana')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO resource (id, business_id, name, working_hours) "
                "VALUES ('res', 'ana', 'Ana', CAST(:wh AS jsonb))"
            ),
            {"wh": HOURS},
        )
        await session.execute(
            text(
                "INSERT INTO service (id, business_id, name, duration_minutes, resource_ids) "
                "VALUES ('svc', 'ana', 'Haircut', 60, CAST('[\"res\"]' AS jsonb))"
            )
        )
        await session.commit()


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url)
    sf = make_session_factory(engine)
    print("Seeding the demo business (Ana's Studio) into Postgres…")
    await seed(sf)

    clock = FixedClock(NOW)
    ids = UuidIdGenerator()
    reminders = SqlReminderStore(sf)
    calendar = SqlCalendar(sf, ids, clock)
    events = ConsoleEvents()
    scheduler = ReminderScheduler(reminders, ids, clock)

    async with httpx.AsyncClient(timeout=60) as client:
        provider = OpenAiProvider(
            api_key=os.environ["FD_LLM_KEY"],
            model=os.environ.get("FD_LLM_MODEL", "deepseek/deepseek-v4-flash"),
            client=client,
            base_url="https://openrouter.ai/api/v1",
        )
        deps = AssistantDeps(
            provider,
            SqlBusinessRepository(sf),
            SqlCustomerRepository(sf, ids),
            SqlConversationRepository(sf),
            SqlServiceRepository(sf),
            SqlAppointmentRepository(sf),
            calendar,
            BookAppointment(calendar, scheduler, events),
            RescheduleAppointment(calendar, scheduler),
            CancelAppointment(calendar, reminders, events),
            ConsoleMessaging(),
            events,
            AutoDecisionGate(approved=False),
            clock,
        )
        assistant = Assistant(deps)

        text_in = "Hi! I'd like a Haircut today at 12:30. Check what's free and book it for me."
        print(f"\n   📱  +59899 → Ana's Studio: {text_in}\n")
        await assistant.handle(
            InboundMessage(Channel.WHATSAPP, "+59899", "+BIZ", text_in, NOW, "demo-1")
        )

    async with sf() as session:
        appts = (
            await session.execute(
                text("SELECT id, starts_at, status FROM appointment WHERE business_id = 'ana'")
            )
        ).all()
        rems = (await session.execute(text("SELECT kind, due_at, status FROM reminder"))).all()
    print("\nPostgres now holds:")
    for row in appts:
        print(f"   appointment {row[0]} · {row[1]:%a %d %b %H:%M} · {row[2]}")
    for row in rems:
        print(f"   reminder {row[0]} · due {row[1]:%a %d %b %H:%M} · {row[2]}")
    await engine.dispose()
    print("\nOK: a WhatsApp message booked a real, persisted appointment in Postgres.")


asyncio.run(main())
