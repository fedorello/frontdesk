"""Tests for the PlatformAnalytics use case (ADR-0012), against in-memory fakes."""

from datetime import UTC, date, datetime

from frontdesk.application.analytics import PlatformAnalytics
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
from frontdesk.infrastructure.system import FixedClock

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def _totals(appointments: AppointmentStatusCounts) -> PlatformTotals:
    return PlatformTotals(
        total_businesses=4,
        signups=SignupCounts(today=1, last_7_days=2, last_30_days=4),
        active_businesses_30d=3,
        total_customers=20,
        total_agent_replies=100,
        appointments=appointments,
        telegram_bots_connected=3,
        owner_telegram_links=2,
        llm_modes=LlmModeCounts(default=3, own=1),
        pending_approvals=1,
    )


def _analytics(
    *,
    appointments: AppointmentStatusCounts,
    funnel: ActivationFunnel,
    series: dict[TimeseriesMetric, list[DailyCount]] | None = None,
    directory: list[BusinessSummary] | None = None,
) -> PlatformAnalytics:
    return PlatformAnalytics(
        InMemoryPlatformSummary(_totals(appointments), funnel),
        InMemoryPlatformTimeseries(series or {}),
        InMemoryBusinessDirectory(directory or []),
        FixedClock(NOW),
    )


async def test_overview_computes_no_show_and_cancellation_rates() -> None:
    appointments = AppointmentStatusCounts(
        pending=0, confirmed=4, completed=4, cancelled=1, no_show=1
    )
    analytics = _analytics(appointments=appointments, funnel=ActivationFunnel(4, 3, 2, 1))

    overview = await analytics.overview()

    assert overview.totals.total_businesses == 4
    assert overview.no_show_rate == 0.1  # 1 of 10
    assert overview.cancellation_rate == 0.1  # 1 of 10


async def test_overview_rates_are_zero_with_no_appointments() -> None:
    analytics = _analytics(
        appointments=AppointmentStatusCounts(0, 0, 0, 0, 0),
        funnel=ActivationFunnel(0, 0, 0, 0),
    )

    overview = await analytics.overview()

    assert overview.no_show_rate == 0.0
    assert overview.cancellation_rate == 0.0
    assert overview.funnel_conversion.booked_pct == 0.0  # zero signed-up → no division


async def test_overview_funnel_conversion_is_relative_to_signups() -> None:
    analytics = _analytics(
        appointments=AppointmentStatusCounts(0, 0, 0, 0, 0),
        funnel=ActivationFunnel(
            signed_up=4, connected_channel=3, received_message=2, booked_appointment=1
        ),
    )

    conversion = (await analytics.overview()).funnel_conversion

    assert conversion.connected_pct == 0.75
    assert conversion.received_message_pct == 0.5
    assert conversion.booked_pct == 0.25


async def test_timeseries_delegates_to_the_repository() -> None:
    points = [DailyCount(date(2026, 1, 1), 3), DailyCount(date(2026, 1, 2), 5)]
    analytics = _analytics(
        appointments=AppointmentStatusCounts(0, 0, 0, 0, 0),
        funnel=ActivationFunnel(0, 0, 0, 0),
        series={TimeseriesMetric.SIGNUPS: points},
    )
    window = DateWindow(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC))

    result = await analytics.timeseries(TimeseriesMetric.SIGNUPS, window)

    assert [p.count for p in result] == [3, 5]


async def test_businesses_returns_a_page_and_total() -> None:
    rows = [
        BusinessSummary(
            business_id=name,
            name=name,
            locale="en",
            timezone="UTC",
            created_at=NOW,
            service_count=1,
            customer_count=1,
            appointments=AppointmentStatusCounts(0, 0, 0, 0, 0),
            agent_reply_count=0,
            last_activity_at=None,
            bot_connected=False,
            uses_own_llm=False,
            owner_telegram_linked=False,
        )
        for name in ("A", "B", "C")
    ]
    analytics = _analytics(
        appointments=AppointmentStatusCounts(0, 0, 0, 0, 0),
        funnel=ActivationFunnel(0, 0, 0, 0),
        directory=rows,
    )
    query = DirectoryQuery(2, 0, DirectorySort.NAME, descending=False, search="")

    page, total = await analytics.businesses(query)

    assert [r.name for r in page] == ["A", "B"]
    assert total == 3
