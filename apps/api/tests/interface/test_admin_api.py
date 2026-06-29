"""Admin analytics endpoints (ADR-0012), unit-tested against in-memory fakes.

The guard is exercised separately (test_admin_guard); here it is None so we test the handlers.
"""

from datetime import UTC, date, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.analytics import PlatformAnalytics
from frontdesk.application.analytics_models import (
    ActivationFunnel,
    AppointmentStatusCounts,
    BusinessSummary,
    DailyCount,
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
from frontdesk.interface.admin_api import build_admin_router

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def _totals() -> PlatformTotals:
    return PlatformTotals(
        total_businesses=2,
        signups=SignupCounts(1, 1, 2),
        active_businesses_30d=1,
        total_customers=3,
        total_agent_replies=9,
        appointments=AppointmentStatusCounts(0, 4, 4, 1, 1),
        telegram_bots_connected=1,
        owner_telegram_links=1,
        llm_modes=LlmModeCounts(default=2, own=0),
        pending_approvals=0,
    )


def _summary(name: str) -> BusinessSummary:
    return BusinessSummary(
        business_id=name,
        name=name,
        locale="en",
        timezone="UTC",
        created_at=NOW,
        service_count=1,
        customer_count=2,
        appointments=AppointmentStatusCounts(0, 1, 0, 0, 0),
        agent_reply_count=3,
        last_activity_at=NOW,
        bot_connected=True,
        uses_own_llm=False,
        owner_telegram_linked=False,
    )


def _client(
    *,
    series: dict[TimeseriesMetric, list[DailyCount]] | None = None,
    directory: list[BusinessSummary] | None = None,
) -> httpx.AsyncClient:
    analytics = PlatformAnalytics(
        InMemoryPlatformSummary(_totals(), ActivationFunnel(2, 1, 1, 1)),
        InMemoryPlatformTimeseries(series or {}),
        InMemoryBusinessDirectory(directory or []),
        FixedClock(NOW),
    )
    app = FastAPI()
    app.include_router(build_admin_router(analytics))
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_overview_returns_totals_funnel_and_rates() -> None:
    async with _client() as client:
        response = await client.get("/api/admin/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["total_businesses"] == 2
    assert body["totals"]["appointments"]["total"] == 10  # the property is exposed
    assert body["funnel"]["signed_up"] == 2
    assert body["no_show_rate"] == 0.1
    assert body["funnel_conversion"]["connected_pct"] == 0.5


async def test_timeseries_returns_daily_points() -> None:
    series = {TimeseriesMetric.SIGNUPS: [DailyCount(date(2026, 1, 1), 3)]}
    async with _client(series=series) as client:
        response = await client.get(
            "/api/admin/timeseries",
            params={
                "metric": "signups",
                "from": "2026-01-01T00:00:00Z",
                "to": "2026-02-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    assert response.json() == [{"day": "2026-01-01", "count": 3}]


async def test_timeseries_rejects_inverted_window() -> None:
    async with _client() as client:
        response = await client.get(
            "/api/admin/timeseries",
            params={
                "metric": "signups",
                "from": "2026-02-01T00:00:00Z",
                "to": "2026-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 422


async def test_timeseries_rejects_unknown_metric() -> None:
    async with _client() as client:
        response = await client.get(
            "/api/admin/timeseries",
            params={
                "metric": "nonsense",
                "from": "2026-01-01T00:00:00Z",
                "to": "2026-02-01T00:00:00Z",
            },
        )

    assert response.status_code == 422


async def test_businesses_returns_a_page_and_total() -> None:
    async with _client(directory=[_summary("A"), _summary("B")]) as client:
        response = await client.get(
            "/api/admin/businesses", params={"limit": 1, "sort": "name", "descending": False}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [row["business_id"] for row in body["items"]] == ["A"]  # page size 1
    assert body["items"][0]["uses_own_llm"] is False


async def test_businesses_rejects_unknown_sort() -> None:
    async with _client() as client:
        response = await client.get("/api/admin/businesses", params={"sort": "nonsense"})

    assert response.status_code == 422
