"""Tests for the in-memory platform-analytics fakes (ADR-0012)."""

from datetime import UTC, date, datetime

import pytest

from frontdesk.application.analytics_models import (
    ActivationFunnel,
    AppointmentStatusCounts,
    BusinessSummary,
    DailyCount,
    DateWindow,
    DirectoryQuery,
    DirectorySort,
    LlmModeCounts,
    PlatformTotals,
    SignupCounts,
    TimeseriesMetric,
)
from frontdesk.infrastructure.memory import (
    InMemoryBusinessDirectory,
    InMemoryPlatformSummary,
    InMemoryPlatformTimeseries,
)

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def _totals() -> PlatformTotals:
    return PlatformTotals(
        total_businesses=3,
        signups=SignupCounts(today=1, last_7_days=2, last_30_days=3),
        active_businesses_30d=2,
        total_customers=10,
        total_agent_replies=42,
        appointments=AppointmentStatusCounts(1, 2, 3, 4, 5),
        telegram_bots_connected=2,
        owner_telegram_links=1,
        llm_modes=LlmModeCounts(default=3, own=0),
        pending_approvals=0,
    )


def _summary(name: str, *, replies: int = 0, last: datetime | None = None) -> BusinessSummary:
    return BusinessSummary(
        business_id=name,
        name=name,
        locale="en",
        timezone="UTC",
        created_at=NOW,
        service_count=1,
        customer_count=replies,  # reuse for a varied numeric column in tests
        appointments=AppointmentStatusCounts(0, replies, 0, 0, 0),
        agent_reply_count=replies,
        last_activity_at=last,
        bot_connected=True,
        uses_own_llm=False,
        owner_telegram_linked=False,
    )


async def test_summary_returns_seeded_totals_and_funnel() -> None:
    funnel = ActivationFunnel(3, 2, 2, 1)
    summary = InMemoryPlatformSummary(_totals(), funnel)

    assert (await summary.totals(NOW)).total_businesses == 3
    assert (await summary.activation_funnel()).booked_appointment == 1


async def test_timeseries_filters_to_the_half_open_window() -> None:
    points = [
        DailyCount(date(2026, 1, 1), 5),
        DailyCount(date(2026, 1, 2), 7),
        DailyCount(date(2026, 1, 3), 9),
    ]
    repo = InMemoryPlatformTimeseries({TimeseriesMetric.SIGNUPS: points})
    window = DateWindow(datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC))

    result = await repo.daily(TimeseriesMetric.SIGNUPS, window)

    assert [p.day for p in result] == [date(2026, 1, 2)]  # start inclusive, end exclusive


async def test_timeseries_unknown_metric_is_empty() -> None:
    repo = InMemoryPlatformTimeseries({})
    window = DateWindow(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC))

    assert await repo.daily(TimeseriesMetric.LLM_USAGE, window) == []


async def test_directory_searches_by_name_case_insensitively() -> None:
    repo = InMemoryBusinessDirectory([_summary("Salon"), _summary("Clinic")])
    query = DirectoryQuery(10, 0, DirectorySort.NAME, descending=False, search="sal")

    rows, total = await repo.page(query)

    assert [r.name for r in rows] == ["Salon"]
    assert total == 1


async def test_directory_sorts_by_replies_descending() -> None:
    repo = InMemoryBusinessDirectory(
        [_summary("A", replies=1), _summary("B", replies=9), _summary("C", replies=5)]
    )
    query = DirectoryQuery(10, 0, DirectorySort.REPLIES, descending=True, search="")

    rows, _ = await repo.page(query)

    assert [r.name for r in rows] == ["B", "C", "A"]


async def test_directory_sorts_by_last_activity_with_none_first_ascending() -> None:
    repo = InMemoryBusinessDirectory([_summary("has", last=NOW), _summary("none", last=None)])
    query = DirectoryQuery(10, 0, DirectorySort.LAST_ACTIVITY, descending=False, search="")

    rows, _ = await repo.page(query)

    assert [r.name for r in rows] == ["none", "has"]  # the -inf surrogate sorts None first


async def test_directory_paginates_and_reports_total_across_pages() -> None:
    repo = InMemoryBusinessDirectory([_summary(name) for name in ("A", "B", "C", "D")])
    query = DirectoryQuery(2, 2, DirectorySort.NAME, descending=False, search="")

    rows, total = await repo.page(query)

    assert [r.name for r in rows] == ["C", "D"]  # the second page
    assert total == 4  # all matches, not just this page


@pytest.mark.parametrize(
    "sort", [DirectorySort.SIGNUP_DATE, DirectorySort.APPOINTMENTS, DirectorySort.CUSTOMERS]
)
async def test_directory_every_sort_key_is_usable(sort: DirectorySort) -> None:
    repo = InMemoryBusinessDirectory([_summary("A", replies=1), _summary("B", replies=2)])
    query = DirectoryQuery(10, 0, sort, descending=False, search="")

    rows, _ = await repo.page(query)

    assert len(rows) == 2  # the sort key resolves without error
