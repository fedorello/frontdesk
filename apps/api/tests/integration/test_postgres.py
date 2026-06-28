"""The SQL adapters pass the shared port contracts on a real Postgres, plus the
database-level guarantees (the exclusion constraint and SKIP LOCKED)."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.enums import AppointmentStatus, Channel
from frontdesk.domain.errors import DoubleBooking
from frontdesk.domain.ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import (
    Customer,
    IntakeAnswer,
    Reminder,
    Resource,
    Service,
    WorkingHours,
)
from frontdesk.infrastructure.postgres.adapters import (
    SqlAccountRepository,
    SqlAppointmentRepository,
    SqlBusinessEraser,
    SqlBusinessRepository,
    SqlCalendar,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlLlmConfigRepository,
    SqlReminderStore,
    SqlResourceRepository,
    SqlServiceRepository,
    SqlTelegramBotRepository,
    SqlUsageStore,
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
    check_usage_store,
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


async def test_booking_a_one_hour_slot_removes_overlapping_15min_slots(
    sessionmaker: Factory,
) -> None:
    # The service is 60 minutes on a 15-minute grid. Booking 09:00 must drop 09:15/09:30/
    # 09:45 — anything that overlaps the hour — even though the step is 15 minutes.
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    service = _service()
    booked = (await calendar.find_availability(service, NOW))[0]

    await calendar.book(service, _resource_id(), _customer(), booked)

    after = await calendar.find_availability(service, NOW)
    assert all(not slot.overlaps(booked) for slot in after)  # no slot inside the booked hour
    assert after[0].starts_at >= booked.ends_at  # the next free slot starts after it ends


async def test_business_eraser_removes_the_business_and_all_its_data(
    sessionmaker: Factory,
) -> None:
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    service = _service()
    slot = (await calendar.find_availability(service, NOW))[0]
    await calendar.book(service, _resource_id(), _customer(), slot)  # customer + appointment
    appointments = SqlAppointmentRepository(sessionmaker)
    assert await appointments.for_business(BusinessId("biz"))  # sanity: there is data

    await SqlBusinessEraser(sessionmaker).erase(BusinessId("biz"))

    assert await appointments.for_business(BusinessId("biz")) == []
    assert await SqlBusinessRepository(sessionmaker).find(BusinessId("biz")) is None


async def test_confirming_a_pending_booking_persists(sessionmaker: Factory) -> None:
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    service = replace(_service(), requires_confirmation=True)
    slot = (await calendar.find_availability(service, NOW))[0]
    booked = await calendar.book(service, _resource_id(), _customer(), slot)
    assert booked.status == AppointmentStatus.PENDING  # owner must confirm

    confirmed = await calendar.confirm(booked.id)

    assert confirmed.status == AppointmentStatus.CONFIRMED
    # Re-read from Postgres: the status stuck.
    stored = await SqlAppointmentRepository(sessionmaker).for_business(booked.business_id)
    assert next(a for a in stored if a.id == booked.id).status == AppointmentStatus.CONFIRMED


async def test_booking_persists_intake_answers(sessionmaker: Factory) -> None:
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    service = _service()
    slot = (await calendar.find_availability(service, NOW))[0]
    intake = (IntakeAnswer("Birth date", "1990-01-01"), IntakeAnswer("Topic", "career"))

    booked = await calendar.book(service, _resource_id(), _customer(), slot, intake)

    # Re-read from Postgres: the answers survive the round-trip.
    stored = await SqlAppointmentRepository(sessionmaker).for_business(booked.business_id)
    appointment = next(a for a in stored if a.id == booked.id)
    assert appointment.intake == intake


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
        ServiceId("svc"),
        BusinessId("biz"),
        "Haircut",
        60,
        resource_ids=(ResourceId("res"),),  # the group "res" owns the schedule
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


async def test_usage_store(sessionmaker: Factory) -> None:
    await check_usage_store(SqlUsageStore(sessionmaker))


async def test_approval_store(sessionmaker: Factory) -> None:
    from frontdesk.application.ports import ApprovalRecord
    from frontdesk.infrastructure.postgres.adapters import SqlApprovalStore

    store = SqlApprovalStore(sessionmaker)
    await store.add(
        ApprovalRecord(
            request_id="req-1",
            business_id="biz",
            tool="issue_refund",
            summary="Refund for ap-1",
            risk="sensitive",
            args={"appointment_id": "ap-1"},
        )
    )

    pending = await store.pending("biz")
    assert len(pending) == 1
    assert pending[0].tool == "issue_refund"
    assert pending[0].args == {"appointment_id": "ap-1"}  # jsonb round-trips
    assert await store.pending("other") == []  # tenant-scoped

    # A foreign tenant can't decide it; the owner can.
    assert await store.decide("req-1", "other", approved=True) is None
    decided = await store.decide("req-1", "biz", approved=True)
    assert decided is not None
    assert decided.status == "approved"
    assert await store.pending("biz") == []  # no longer pending


async def test_service_groups_e2e_same_group_collides_different_group_parallel(
    sessionmaker: Factory,
) -> None:
    """End-to-end on real Postgres: same-group services share one calendar (and the gist
    exclusion constraint), so they can't overlap; different-group services book in parallel.
    This is the core service-groups guarantee, through the real SqlCalendar + DB constraint."""
    services = SqlServiceRepository(sessionmaker)
    resources = SqlResourceRepository(sessionmaker)
    calendar = SqlCalendar(sessionmaker, SequentialIdGenerator("ap"), FixedClock(NOW))
    week = tuple(WorkingHours(day, time(9), time(17)) for day in range(7))

    # The seed gives us group "res" + service "svc". Add a second group "res2" and two more
    # services: one in the SAME group as "svc", one in the different group "res2".
    await resources.upsert(Resource(ResourceId("res2"), BusinessId("biz"), "Bob", week))
    same_group = Service(
        ServiceId("svc-same"), BusinessId("biz"), "Reading", 60, resource_ids=(ResourceId("res"),)
    )
    other_group = Service(
        ServiceId("svc-other"),
        BusinessId("biz"),
        "Coaching",
        60,
        resource_ids=(ResourceId("res2"),),
    )
    await services.upsert(same_group)
    await services.upsert(other_group)

    seeded = _service()  # "svc", in group "res"
    slot = (await calendar.find_availability(seeded, NOW))[0]
    await calendar.book(seeded, ResourceId("res"), _customer(), slot)

    # SAME group: the slot vanishes from the sibling service's availability, and booking it
    # raises DoubleBooking — one specialist can't be in two appointments at once.
    sibling_slots = await calendar.find_availability(same_group, NOW)
    assert all(not s.overlaps(slot) for s in sibling_slots)
    with pytest.raises(DoubleBooking):
        await calendar.book(same_group, ResourceId("res"), _customer(), slot)

    # DIFFERENT group: still offered at the SAME time and bookable in parallel (a different
    # specialist with an independent calendar).
    other_slots = await calendar.find_availability(other_group, NOW)
    assert any(s.starts_at == slot.starts_at for s in other_slots)
    parallel = await calendar.book(other_group, ResourceId("res2"), _customer(), slot)
    assert parallel.slot.starts_at == slot.starts_at
