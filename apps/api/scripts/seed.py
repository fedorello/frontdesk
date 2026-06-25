"""Idempotent demo seed: a business the web chat can talk to and book with.

Run after migrations (the compose `seed` service does this automatically).
"""

import asyncio
import json

from sqlalchemy import text

from frontdesk.core.settings import Settings
from frontdesk.infrastructure.db import create_engine, make_session_factory

_HOURS = json.dumps([{"weekday": d, "opens": "00:00:00", "closes": "23:59:59"} for d in range(7)])
_KNOWLEDGE = json.dumps(
    [
        {"question": "opening hours", "answer": "We are open 24/7."},
        {"question": "price", "answer": "A Haircut is 25 USD."},
        {"question": "location", "answer": "We are at 5 Rivera Street, downtown."},
    ]
)

_STATEMENTS = [
    (
        "INSERT INTO business (id, name, timezone, knowledge) "
        "VALUES ('ana', 'Ana Studio', 'UTC', CAST(:kb AS jsonb)) ON CONFLICT (id) DO NOTHING",
        {"kb": _KNOWLEDGE},
    ),
    (
        "INSERT INTO channel_binding (channel, address, business_id) "
        "VALUES ('whatsapp', '+BIZ', 'ana') ON CONFLICT DO NOTHING",
        {},
    ),
    (
        "INSERT INTO resource (id, business_id, name, working_hours) "
        "VALUES ('res', 'ana', 'Ana', CAST(:wh AS jsonb)) ON CONFLICT (id) DO NOTHING",
        {"wh": _HOURS},
    ),
    (
        "INSERT INTO service (id, business_id, name, duration_minutes, resource_ids) "
        "VALUES ('svc', 'ana', 'Haircut', 60, CAST('[\"res\"]' AS jsonb)) ON CONFLICT (id) DO NOTHING",
        {},
    ),
]


async def main() -> None:
    engine = create_engine(Settings().database_url)
    sessions = make_session_factory(engine)
    async with sessions() as session:
        for sql, params in _STATEMENTS:
            await session.execute(text(sql), params)
        await session.commit()
    await engine.dispose()
    print("seeded demo business 'Ana Studio' (service: Haircut, WhatsApp +BIZ)")


asyncio.run(main())
