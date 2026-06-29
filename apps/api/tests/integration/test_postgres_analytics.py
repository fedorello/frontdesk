"""Integration tests for the Postgres analytics adapters (ADR-0012), on a real database.

The base fixture seeds one business ('biz') with a customer ('cus') and one confirmed
appointment ('appt'). Each test layers a deterministic world on top and asserts the
aggregation. The shared port behavior (search/sort/pagination, window bucketing) mirrors the
in-memory fakes' unit tests.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.application.analytics_models import (
    DateWindow,
    DirectoryQuery,
    DirectorySort,
    TimeseriesMetric,
)
from frontdesk.infrastructure.postgres.analytics import (
    SqlBusinessDirectoryRepository,
    SqlPlatformSummaryRepository,
    SqlPlatformTimeseriesRepository,
)

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
Sf = async_sessionmaker[AsyncSession]


async def _exec(sf: Sf, sql: str, **params: object) -> None:
    async with sf() as session:
        await session.execute(text(sql), params)
        await session.commit()


async def _business(sf: Sf, business_id: str) -> None:
    await _exec(
        sf,
        "INSERT INTO business (id, name, timezone) VALUES (:id, :id, 'UTC')",
        id=business_id,
    )


async def _account(
    sf: Sf, account_id: str, business_id: str | None, created_at: datetime, role: str = "owner"
) -> None:
    await _exec(
        sf,
        "INSERT INTO account (id, email, password_hash, business_id, role, created_at) "
        "VALUES (:id, :id, 'h', :bid, :role, :created)",
        id=account_id,
        bid=business_id,
        role=role,
        created=created_at,
    )


async def _customer(sf: Sf, customer_id: str, business_id: str, created_at: datetime) -> None:
    await _exec(
        sf,
        "INSERT INTO customer (id, business_id, channel, address, created_at) "
        "VALUES (:id, :bid, 'telegram', :id, :created)",
        id=customer_id,
        bid=business_id,
        created=created_at,
    )


async def _message(sf: Sf, business_id: str, customer_id: str, role: str, at: datetime) -> None:
    await _exec(
        sf,
        "INSERT INTO message (business_id, customer_id, role, body, at) "
        "VALUES (:bid, :cid, :role, 'x', :at)",
        bid=business_id,
        cid=customer_id,
        role=role,
        at=at,
    )


async def _appointment(
    sf: Sf, appt_id: str, business_id: str, status: str, created_at: datetime
) -> None:
    # A unique resource_id per appointment so the no-double-book exclusion never trips.
    await _exec(
        sf,
        "INSERT INTO appointment (id, business_id, service_id, resource_id, customer_id, "
        "starts_at, ends_at, status, created_at) VALUES (:id, :bid, 'svc', :id, 'cus', "
        "'2027-01-01T00:00:00+00', '2027-01-01T01:00:00+00', :status, :created)",
        id=appt_id,
        bid=business_id,
        status=status,
        created=created_at,
    )


async def _seed_world(sf: Sf) -> None:
    """A complete, deterministic platform state layered on the base 'biz' seed."""
    for business_id in ("biz2", "biz3"):
        await _business(sf, business_id)
    await _account(sf, "acc1", "biz", NOW)
    await _account(sf, "acc2", "biz2", NOW - timedelta(days=3))
    await _account(sf, "acc3", "biz3", NOW - timedelta(days=20))
    await _account(sf, "admin", None, NOW, role="admin")  # no business → not a signup
    await _customer(sf, "cus2", "biz2", NOW)
    await _exec(
        sf,
        "INSERT INTO channel_binding (channel, address, business_id) VALUES "
        "('telegram', '@bot2', 'biz2')",
    )
    await _message(sf, "biz", "cus", "assistant", NOW)
    await _message(sf, "biz", "cus", "customer", NOW)
    await _message(sf, "biz", "cus", "assistant", NOW - timedelta(days=40))  # old, still a reply
    await _message(sf, "biz2", "cus2", "customer", NOW - timedelta(days=3))
    await _appointment(sf, "ap_cancel", "biz", "cancelled", NOW)
    await _appointment(sf, "ap_done", "biz2", "completed", NOW - timedelta(days=1))
    await _appointment(sf, "ap_noshow", "biz3", "no_show", NOW - timedelta(days=2))
    await _exec(
        sf,
        "INSERT INTO telegram_bot (business_id, bot_token, secret_token, username) "
        "VALUES ('biz2', 't', 's', 'b2')",
    )
    await _exec(
        sf,
        "INSERT INTO owner_telegram_link (business_id, chat_id, telegram_name) "
        "VALUES ('biz', '1', 'Owner')",
    )
    await _exec(sf, "INSERT INTO llm_config (business_id, mode) VALUES ('biz', 'own')")
    await _exec(sf, "INSERT INTO llm_config (business_id, mode) VALUES ('biz2', 'default')")
    await _exec(
        sf,
        "INSERT INTO approval (request_id, business_id, tool, summary, risk, status) "
        "VALUES ('a1', 'biz', 't', 's', 'sensitive', 'pending')",
    )


async def test_totals_aggregates_every_headline_count(sessionmaker: Sf) -> None:
    await _seed_world(sessionmaker)

    totals = await SqlPlatformSummaryRepository(sessionmaker).totals(NOW)

    assert totals.total_businesses == 3
    assert (totals.signups.today, totals.signups.last_7_days, totals.signups.last_30_days) == (
        1,
        2,
        3,
    )
    assert totals.active_businesses_30d == 2  # biz (msg at NOW) + biz2 (msg at NOW-3d)
    assert totals.total_customers == 2  # cus + cus2
    assert totals.total_agent_replies == 2  # two assistant messages
    appointments = totals.appointments
    assert (appointments.confirmed, appointments.completed) == (1, 1)  # base 'appt' + ap_done
    assert (appointments.cancelled, appointments.no_show, appointments.pending) == (1, 1, 0)
    assert totals.telegram_bots_connected == 1
    assert totals.owner_telegram_links == 1
    assert (totals.llm_modes.own, totals.llm_modes.default) == (1, 2)  # default = 3 - 1 own
    assert totals.pending_approvals == 1


async def test_activation_funnel_counts_businesses_per_stage(sessionmaker: Sf) -> None:
    await _seed_world(sessionmaker)

    funnel = await SqlPlatformSummaryRepository(sessionmaker).activation_funnel()

    assert funnel.signed_up == 3  # acc1/2/3 (admin has no business)
    assert funnel.connected_channel == 2  # biz (+100) + biz2 (@bot2)
    assert funnel.received_message == 2  # biz + biz2 have a customer message
    assert funnel.booked_appointment == 3  # biz + biz2 + biz3 have an appointment


async def test_bookings_timeseries_buckets_by_utc_day_half_open(sessionmaker: Sf) -> None:
    await _appointment(
        sessionmaker, "a1", "biz", "confirmed", datetime(2026, 3, 10, 23, 30, tzinfo=UTC)
    )
    await _appointment(
        sessionmaker, "a2", "biz", "confirmed", datetime(2026, 3, 11, 0, 30, tzinfo=UTC)
    )
    await _appointment(
        sessionmaker, "a3", "biz", "confirmed", datetime(2026, 3, 11, 10, 0, tzinfo=UTC)
    )
    await _appointment(
        sessionmaker, "a4", "biz", "confirmed", datetime(2026, 3, 12, 0, 0, tzinfo=UTC)
    )
    window = DateWindow(datetime(2026, 3, 10, tzinfo=UTC), datetime(2026, 3, 12, tzinfo=UTC))

    rows = await SqlPlatformTimeseriesRepository(sessionmaker).daily(
        TimeseriesMetric.BOOKINGS, window
    )

    counts = {row.day.isoformat(): row.count for row in rows}
    assert counts == {"2026-03-10": 1, "2026-03-11": 2}  # 03-12 excluded (end is exclusive)


async def test_llm_usage_timeseries_sums_per_day_across_businesses(sessionmaker: Sf) -> None:
    await _business(sessionmaker, "biz2")
    await _exec(
        sessionmaker,
        "INSERT INTO usage_counter (business_id, day, count) VALUES ('biz', '2026-04-01', 3)",
    )
    await _exec(
        sessionmaker,
        "INSERT INTO usage_counter (business_id, day, count) VALUES ('biz2', '2026-04-01', 2)",
    )
    await _exec(
        sessionmaker,
        "INSERT INTO usage_counter (business_id, day, count) VALUES ('biz', '2026-04-02', 5)",
    )
    window = DateWindow(datetime(2026, 4, 1, tzinfo=UTC), datetime(2026, 4, 3, tzinfo=UTC))

    rows = await SqlPlatformTimeseriesRepository(sessionmaker).daily(
        TimeseriesMetric.LLM_USAGE, window
    )

    assert {row.day.isoformat(): row.count for row in rows} == {"2026-04-01": 5, "2026-04-02": 5}


async def test_directory_rolls_up_counts_per_business(sessionmaker: Sf) -> None:
    await _account(sessionmaker, "acc1", "biz", NOW)
    await _message(sessionmaker, "biz", "cus", "assistant", NOW)
    await _message(sessionmaker, "biz", "cus", "assistant", NOW + timedelta(hours=1))
    await _exec(sessionmaker, "INSERT INTO llm_config (business_id, mode) VALUES ('biz', 'own')")
    query = DirectoryQuery(10, 0, DirectorySort.NAME, descending=False, search="")

    rows, total = await SqlBusinessDirectoryRepository(sessionmaker).page(query)

    assert total == 1
    row = rows[0]
    assert row.business_id == "biz"
    assert row.agent_reply_count == 2
    assert row.customer_count == 1  # base 'cus'
    assert row.appointments.confirmed == 1  # base 'appt'
    assert row.uses_own_llm is True
    assert row.last_activity_at == NOW + timedelta(hours=1)  # the most recent message


async def test_directory_searches_sorts_and_paginates(sessionmaker: Sf) -> None:
    await _business(sessionmaker, "Alpha")
    await _business(sessionmaker, "Beta")
    # Names are 'biz', 'Alpha', 'Beta'; a case-insensitive 'a' matches Alpha and Beta.
    query = DirectoryQuery(1, 0, DirectorySort.NAME, descending=False, search="a")

    rows, total = await SqlBusinessDirectoryRepository(sessionmaker).page(query)

    assert total == 2  # Alpha, Beta (case-insensitive ILIKE)
    assert [r.name for r in rows] == ["Alpha"]  # page size 1, sorted by name asc


async def test_directory_orders_null_last_activity_first_ascending(sessionmaker: Sf) -> None:
    await _business(sessionmaker, "biz2")
    await _customer(sessionmaker, "cusb2", "biz2", NOW)
    await _message(sessionmaker, "biz2", "cusb2", "assistant", NOW)
    query = DirectoryQuery(10, 0, DirectorySort.LAST_ACTIVITY, descending=False, search="")

    rows, _ = await SqlBusinessDirectoryRepository(sessionmaker).page(query)

    # biz has no messages (None last_activity); ascending sorts the NULL first.
    assert [r.business_id for r in rows] == ["biz", "biz2"]
