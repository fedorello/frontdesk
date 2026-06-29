"""Tests for the platform-analytics read models (ADR-0012)."""

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
    FunnelConversion,
    LlmModeCounts,
    Overview,
    PlatformTotals,
    SignupCounts,
    TimeseriesMetric,
)


def test_date_window_accepts_a_forward_utc_range() -> None:
    window = DateWindow(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 8, tzinfo=UTC))

    assert window.start < window.end


def test_date_window_rejects_a_naive_bound() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        DateWindow(datetime(2026, 1, 1), datetime(2026, 1, 8, tzinfo=UTC))  # noqa: DTZ001


def test_date_window_rejects_an_inverted_range() -> None:
    with pytest.raises(ValueError, match="after"):
        DateWindow(datetime(2026, 1, 8, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC))


def test_appointment_status_counts_total_sums_every_status() -> None:
    counts = AppointmentStatusCounts(pending=1, confirmed=2, completed=3, cancelled=4, no_show=5)

    assert counts.total == 15


def test_timeseries_metric_and_directory_sort_have_stable_values() -> None:
    assert TimeseriesMetric("signups") is TimeseriesMetric.SIGNUPS
    assert DirectorySort("last_activity") is DirectorySort.LAST_ACTIVITY


def test_overview_holds_totals_funnel_and_derived_rates() -> None:
    totals = PlatformTotals(
        total_businesses=2,
        signups=SignupCounts(today=1, last_7_days=1, last_30_days=2),
        active_businesses_30d=1,
        total_customers=3,
        total_agent_replies=10,
        appointments=AppointmentStatusCounts(1, 1, 1, 1, 1),
        telegram_bots_connected=1,
        owner_telegram_links=1,
        llm_modes=LlmModeCounts(default=2, own=0),
        pending_approvals=0,
    )
    funnel = ActivationFunnel(
        signed_up=2, connected_channel=1, received_message=1, booked_appointment=1
    )

    overview = Overview(
        totals=totals,
        funnel=funnel,
        funnel_conversion=FunnelConversion(0.5, 0.5, 0.5),
        no_show_rate=0.2,
        cancellation_rate=0.2,
    )

    assert overview.totals.total_businesses == 2
    assert overview.funnel.signed_up == 2
    assert overview.no_show_rate == 0.2


def test_business_summary_carries_counts_and_config_only() -> None:
    summary = BusinessSummary(
        business_id="b1",
        name="Salon",
        locale="en",
        timezone="UTC",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        service_count=2,
        customer_count=5,
        appointments=AppointmentStatusCounts(0, 1, 0, 0, 0),
        agent_reply_count=7,
        last_activity_at=None,
        bot_connected=True,
        uses_own_llm=False,
        owner_telegram_linked=True,
    )

    assert summary.appointments.total == 1
    assert summary.last_activity_at is None


def test_daily_count_and_directory_query_construct() -> None:
    point = DailyCount(date(2026, 1, 1), 3)
    query = DirectoryQuery(
        limit=8, offset=0, sort=DirectorySort.SIGNUP_DATE, descending=True, search=""
    )

    assert point.count == 3
    assert query.sort is DirectorySort.SIGNUP_DATE
