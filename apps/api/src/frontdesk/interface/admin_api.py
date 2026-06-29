"""Cross-tenant analytics endpoints for the admin dashboard (ADR-0012).

Read-only and aggregate-only: the response models carry counts and config — never a customer's
message, address, or intake answer — so the privacy boundary holds at the API surface too.
Mounted behind the admin guard in the composition root.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from frontdesk.application.analytics import PlatformAnalytics
from frontdesk.application.analytics_models import (
    DateWindow,
    DirectoryQuery,
    DirectorySort,
    TimeseriesMetric,
)

Guard = Callable[..., Awaitable[None]] | None

# Server-capped page size for the directory, mirroring read_api: the client asks, the server caps.
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignupCountsView(_FromAttributes):
    today: int
    last_7_days: int
    last_30_days: int


class AppointmentStatusCountsView(_FromAttributes):
    pending: int
    confirmed: int
    completed: int
    cancelled: int
    no_show: int
    total: int


class LlmModeCountsView(_FromAttributes):
    default: int
    own: int


class PlatformTotalsView(_FromAttributes):
    total_businesses: int
    signups: SignupCountsView
    active_businesses_30d: int
    total_customers: int
    total_agent_replies: int
    appointments: AppointmentStatusCountsView
    telegram_bots_connected: int
    owner_telegram_links: int
    llm_modes: LlmModeCountsView
    pending_approvals: int


class ActivationFunnelView(_FromAttributes):
    signed_up: int
    connected_channel: int
    received_message: int
    booked_appointment: int


class FunnelConversionView(_FromAttributes):
    connected_pct: float
    received_message_pct: float
    booked_pct: float


class OverviewView(_FromAttributes):
    totals: PlatformTotalsView
    funnel: ActivationFunnelView
    funnel_conversion: FunnelConversionView
    no_show_rate: float
    cancellation_rate: float


class DailyCountView(_FromAttributes):
    day: date
    count: int


class BusinessSummaryView(_FromAttributes):
    business_id: str
    name: str
    locale: str
    timezone: str
    created_at: datetime
    service_count: int
    customer_count: int
    appointments: AppointmentStatusCountsView
    agent_reply_count: int
    last_activity_at: datetime | None
    bot_connected: bool
    uses_own_llm: bool
    owner_telegram_linked: bool


class BusinessPageView(BaseModel):
    items: list[BusinessSummaryView]
    total: int  # matching businesses across all pages, for the page count


def _as_utc(moment: datetime) -> datetime:
    """Treat a naive bound as UTC; the API contract is UTC (§7.7)."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def build_admin_router(analytics: PlatformAnalytics, guard: Guard = None) -> APIRouter:
    router = APIRouter(
        prefix="/api/admin", dependencies=[Depends(guard)] if guard is not None else []
    )

    @router.get("/overview")
    async def overview() -> OverviewView:
        return OverviewView.model_validate(await analytics.overview())

    @router.get("/timeseries")
    async def timeseries(
        metric: TimeseriesMetric,
        start: datetime = Query(alias="from"),
        end: datetime = Query(alias="to"),
    ) -> list[DailyCountView]:
        window_start, window_end = _as_utc(start), _as_utc(end)
        if window_end <= window_start:
            raise HTTPException(422, "'from' must be before 'to'")
        points = await analytics.timeseries(metric, DateWindow(window_start, window_end))
        return [DailyCountView.model_validate(point) for point in points]

    @router.get("/businesses")
    async def businesses(
        limit: int = _DEFAULT_PAGE_SIZE,
        offset: int = 0,
        sort: DirectorySort = DirectorySort.SIGNUP_DATE,
        descending: bool = True,
        q: str = "",
    ) -> BusinessPageView:
        query = DirectoryQuery(
            limit=min(max(limit, 1), _MAX_PAGE_SIZE),
            offset=max(offset, 0),
            sort=sort,
            descending=descending,
            search=q,
        )
        items, total = await analytics.businesses(query)
        return BusinessPageView(
            items=[BusinessSummaryView.model_validate(item) for item in items], total=total
        )

    return router
