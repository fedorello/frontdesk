"""The SQL adapters pass the shared port contracts on a real Postgres, plus the
database-level guarantees (the exclusion constraint and SKIP LOCKED)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.enums import Channel
from frontdesk.domain.errors import DoubleBooking
from frontdesk.domain.ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import Customer, Reminder, Service
from frontdesk.infrastructure.postgres.adapters import (
    SqlAccountRepository,
    SqlAppointmentRepository,
    SqlBusinessRepository,
    SqlCalendar,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlLlmConfigRepository,
    SqlReminderStore,
    SqlResourceRepository,
    SqlServiceRepository,
    SqlTelegramBotRepository,
)
from frontdesk.infrastructure.secrets import FernetCipher
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from tests.port_contracts import (
    NOW,
    check_account_repository,
    check_appointment_repository,
    check_business_repository,
    check_business_write,
    check_calendar,
    check_conversation_repository,
    check_customer_repository,
    check_llm_config_repository,
    check_reminder_store,
    check_resource_write,
    check_service_write,
    check_telegram_bot_repository,
)

Factory = async_sessionmaker[AsyncSession]


async def test_business_repository(sessionmaker: Factory) -> None:
    await check_business_repository(SqlBusinessRepository(sessionmaker))


async def test_customer_repository(sessionmaker: Factory) -> None:
    await check_customer_repository(SqlCustomerRepository(sessionmaker, SequentialIdGenerator("c")))


async def test_conversation_repository(sessionmaker: Factory) -> None:
    await check_conversation_repository(SqlConversationRepository(sessionmaker))


async def test_appointment_repository(sessionmaker: Factory) -> None:
    await check_appointment_repository(SqlAppointmentRepository(sessionmaker))


async def test_reminder_store(sessionmaker: Factory) -> None:
    await check_reminder_store(SqlReminderStore(sessionmaker))


async def test_calendar(sessionmaker: Factory) -> None:
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    await check_calendar(calendar)


async def test_telegram_bot_repository(sessionmaker: Factory) -> None:
    cipher = FernetCipher(FernetCipher.generate_key())
    await check_telegram_bot_repository(SqlTelegramBotRepository(sessionmaker, cipher))


async def test_llm_config_repository(sessionmaker: Factory) -> None:
    cipher = FernetCipher(FernetCipher.generate_key())
    await check_llm_config_repository(SqlLlmConfigRepository(sessionmaker, cipher))


async def test_double_book_rejected_by_db_constraint(sessionmaker: Factory) -> None:
    # Insert two overlapping appointments for the same resource, bypassing the
    # application checks — the gist EXCLUDE constraint must reject the second.
    start = datetime(2026, 6, 26, 14, 0, tzinfo=UTC)
    rows = {
        "bid": "biz",
        "sid": "svc",
        "rid": "res",
        "cid": "cus",
        "start": start,
        "end": start + timedelta(hours=1),
    }
    async with sessionmaker() as session:
        await session.execute(
            text(
                "INSERT INTO appointment "
                "(id, business_id, service_id, resource_id, customer_id, starts_at, ends_at) "
                "VALUES ('x1', :bid, :sid, :rid, :cid, :start, :end)"
            ),
            rows,
        )
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    "INSERT INTO appointment "
                    "(id, business_id, service_id, resource_id, customer_id, starts_at, ends_at) "
                    "VALUES ('x2', :bid, :sid, :rid, :cid, :start, :end)"
                ),
                rows,
            )


async def test_calendar_book_maps_constraint_to_double_booking(sessionmaker: Factory) -> None:
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    slots = await calendar.find_availability(_service(), NOW)
    await calendar.book(_service(), _resource_id(), _customer(), slots[0])
    with pytest.raises(DoubleBooking):
        await calendar.book(_service(), _resource_id(), _customer(), slots[0])


async def test_claim_due_skips_locked_rows(sessionmaker: Factory) -> None:
    store = SqlReminderStore(sessionmaker)
    await store.schedule([_reminder("r1"), _reminder("r2")])

    # One transaction claims (and holds) the due rows; a concurrent claim must
    # skip the locked rows and get nothing.
    async with sessionmaker() as locking:
        locked = (
            await locking.execute(
                text(
                    "SELECT id FROM reminder WHERE status = 'pending' AND due_at <= :now "
                    "FOR UPDATE SKIP LOCKED"
                ),
                {"now": NOW},
            )
        ).all()
        assert len(locked) == 2
        concurrent = await store.claim_due(NOW)
        assert concurrent == []  # all rows are locked by the open transaction


def _service() -> Service:
    return Service(
        ServiceId("svc"), BusinessId("biz"), "Haircut", 60, resource_ids=(ResourceId("res"),)
    )


def _resource_id() -> ResourceId:
    return ResourceId("res")


def _customer() -> Customer:
    return Customer(CustomerId("cus"), BusinessId("biz"), Channel.WHATSAPP, "+CUST")


def _reminder(rid: str) -> Reminder:
    return Reminder(
        ReminderId(rid), BusinessId("biz"), AppointmentId("appt"), NOW - timedelta(minutes=1), "24h"
    )


async def test_business_write(sessionmaker: Factory) -> None:
    await check_business_write(SqlBusinessRepository(sessionmaker))


async def test_service_write(sessionmaker: Factory) -> None:
    await check_service_write(SqlServiceRepository(sessionmaker))


async def test_resource_write(sessionmaker: Factory) -> None:
    await check_resource_write(SqlResourceRepository(sessionmaker))


async def test_account_repository(sessionmaker: Factory) -> None:
    await check_account_repository(SqlAccountRepository(sessionmaker))
