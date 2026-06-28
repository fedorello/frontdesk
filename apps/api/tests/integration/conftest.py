"""Real-Postgres fixtures: recreate the schema and seed the contract data."""

import json
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.core.settings import Settings
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.postgres.schema import CREATE_STATEMENTS, DROP_STATEMENTS

_HOURS = json.dumps(
    [{"weekday": day, "opens": "09:00:00", "closes": "17:00:00"} for day in range(7)]
)


@pytest_asyncio.fixture
async def sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(Settings().database_url)
    async with engine.begin() as conn:
        for statement in DROP_STATEMENTS:
            await conn.execute(text(statement))
        for statement in CREATE_STATEMENTS:
            await conn.execute(text(statement))
        await conn.execute(
            text("INSERT INTO business (id, name, timezone) VALUES ('biz', 'Studio', 'UTC')")
        )
        await conn.execute(
            text(
                "INSERT INTO channel_binding (channel, address, business_id) "
                "VALUES ('whatsapp', '+100', 'biz')"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO resource (id, business_id, name, working_hours) "
                "VALUES ('res', 'biz', 'Ana', CAST(:wh AS jsonb))"
            ),
            {"wh": _HOURS},
        )
        await conn.execute(
            # No working_hours on the service — the schedule lives on its group ("res").
            text(
                "INSERT INTO service "
                "(id, business_id, name, duration_minutes, resource_ids) "
                "VALUES ('svc', 'biz', 'Haircut', 60, CAST('[\"res\"]' AS jsonb))"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO customer (id, business_id, channel, address) "
                "VALUES ('cus', 'biz', 'whatsapp', '+CUST')"
            )
        )
        # An out-of-window appointment so reminder FKs resolve without affecting
        # availability near NOW (2026-06-26).
        await conn.execute(
            text(
                "INSERT INTO appointment "
                "(id, business_id, service_id, resource_id, customer_id, "
                "starts_at, ends_at, status)"
                " VALUES ('appt', 'biz', 'svc', 'res', 'cus', "
                "'2026-09-01T09:00:00+00', '2026-09-01T10:00:00+00', 'confirmed')"
            )
        )
    factory = make_session_factory(engine)
    yield factory
    await engine.dispose()
