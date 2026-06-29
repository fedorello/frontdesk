"""Postgres adapters for the platform-analytics ports (ADR-0012).

Cross-tenant, read-only aggregation: every figure is a count or a sum produced by SQL —
never a customer's message, address, or intake answer. Each method runs a single aggregating
statement (no per-business round-trips). See docs/design/admin-dashboard.md.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from frontdesk.domain.enums import AppointmentStatus, MessageRole

Row = Any  # a SQLAlchemy Row; matches the convention in adapters.py (their typing is awkward)

_SIGNUP_WINDOW_7 = 7
_SIGNUP_WINDOW_30 = 30
_OWN_LLM = "own"  # llm_config.mode for a bring-your-own key (matches tenancy.py)


def _status_params() -> dict[str, object]:
    """The appointment-status literals as bind params, so the SQL holds no magic strings."""
    return {
        "pending": AppointmentStatus.PENDING.value,
        "confirmed": AppointmentStatus.CONFIRMED.value,
        "completed": AppointmentStatus.COMPLETED.value,
        "cancelled": AppointmentStatus.CANCELLED.value,
        "no_show": AppointmentStatus.NO_SHOW.value,
    }


def _appointment_counts(row: Row) -> AppointmentStatusCounts:
    return AppointmentStatusCounts(
        pending=row.ap_pending,
        confirmed=row.ap_confirmed,
        completed=row.ap_completed,
        cancelled=row.ap_cancelled,
        no_show=row.ap_no_show,
    )


_TOTALS_SQL = """
SELECT
  (SELECT count(*) FROM business) AS total_businesses,
  (SELECT count(*) FROM account WHERE business_id IS NOT NULL AND created_at >= :today)
    AS signups_today,
  (SELECT count(*) FROM account WHERE business_id IS NOT NULL AND created_at >= :d7)
    AS signups_7,
  (SELECT count(*) FROM account WHERE business_id IS NOT NULL AND created_at >= :d30)
    AS signups_30,
  (SELECT count(DISTINCT business_id) FROM message WHERE at >= :d30) AS active_30,
  (SELECT count(*) FROM customer) AS customers,
  (SELECT count(*) FROM message WHERE role = :assistant) AS replies,
  (SELECT count(*) FROM appointment WHERE status = :pending) AS ap_pending,
  (SELECT count(*) FROM appointment WHERE status = :confirmed) AS ap_confirmed,
  (SELECT count(*) FROM appointment WHERE status = :completed) AS ap_completed,
  (SELECT count(*) FROM appointment WHERE status = :cancelled) AS ap_cancelled,
  (SELECT count(*) FROM appointment WHERE status = :no_show) AS ap_no_show,
  (SELECT count(*) FROM telegram_bot) AS bots,
  (SELECT count(*) FROM owner_telegram_link) AS links,
  (SELECT count(*) FROM llm_config WHERE mode = :own) AS llm_own,
  (SELECT count(*) FROM approval WHERE status = 'pending') AS pending_approvals
"""

_FUNNEL_SQL = """
SELECT
  (SELECT count(*) FROM account WHERE business_id IS NOT NULL) AS signed_up,
  (SELECT count(DISTINCT business_id) FROM channel_binding) AS connected,
  (SELECT count(DISTINCT business_id) FROM message WHERE role = :customer) AS messaged,
  (SELECT count(DISTINCT business_id) FROM appointment) AS booked
"""


class SqlPlatformSummaryRepository:
    """Headline totals and the activation funnel, across all tenants (ADR-0012)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def totals(self, now: datetime) -> PlatformTotals:
        today = datetime(now.year, now.month, now.day, tzinfo=UTC)
        params: dict[str, object] = {
            "today": today,
            "d7": now - timedelta(days=_SIGNUP_WINDOW_7),
            "d30": now - timedelta(days=_SIGNUP_WINDOW_30),
            "assistant": MessageRole.ASSISTANT.value,
            "own": _OWN_LLM,
            **_status_params(),
        }
        async with self._sf() as session:
            row = (await session.execute(text(_TOTALS_SQL), params)).one()
        total, own = row.total_businesses, row.llm_own
        return PlatformTotals(
            total_businesses=total,
            signups=SignupCounts(row.signups_today, row.signups_7, row.signups_30),
            active_businesses_30d=row.active_30,
            total_customers=row.customers,
            total_agent_replies=row.replies,
            appointments=_appointment_counts(row),
            telegram_bots_connected=row.bots,
            owner_telegram_links=row.links,
            llm_modes=LlmModeCounts(default=total - own, own=own),
            pending_approvals=row.pending_approvals,
        )

    async def activation_funnel(self) -> ActivationFunnel:
        async with self._sf() as session:
            row = (
                await session.execute(text(_FUNNEL_SQL), {"customer": MessageRole.CUSTOMER.value})
            ).one()
        return ActivationFunnel(row.signed_up, row.connected, row.messaged, row.booked)


def _daily_count_sql(table: str, ts_column: str, extra_where: str = "") -> str:
    """A per-UTC-day row count over a half-open [start, end) window of one timestamp column."""
    return (
        f"SELECT (({ts_column}) AT TIME ZONE 'UTC')::date AS day, count(*) AS n "
        f"FROM {table} WHERE {ts_column} >= :start AND {ts_column} < :end {extra_where} "
        "GROUP BY day ORDER BY day"
    )


def _signups_query(window: DateWindow) -> tuple[str, dict[str, object]]:
    sql = _daily_count_sql("account", "created_at", "AND business_id IS NOT NULL")
    return sql, {"start": window.start, "end": window.end}


def _bookings_query(window: DateWindow) -> tuple[str, dict[str, object]]:
    return _daily_count_sql("appointment", "created_at"), {"start": window.start, "end": window.end}


def _new_customers_query(window: DateWindow) -> tuple[str, dict[str, object]]:
    return _daily_count_sql("customer", "created_at"), {"start": window.start, "end": window.end}


def _replies_query(window: DateWindow) -> tuple[str, dict[str, object]]:
    sql = _daily_count_sql("message", "at", "AND role = :role")
    return sql, {"start": window.start, "end": window.end, "role": MessageRole.ASSISTANT.value}


def _llm_usage_query(window: DateWindow) -> tuple[str, dict[str, object]]:
    # usage_counter already stores one row per (business, day) with a per-day count, keyed by a
    # text 'YYYY-MM-DD' day — so we sum across businesses and compare ISO date strings.
    sql = (
        "SELECT day::date AS day, sum(count) AS n FROM usage_counter "
        "WHERE day >= :start_day AND day < :end_day GROUP BY day ORDER BY day"
    )
    return sql, {
        "start_day": window.start.date().isoformat(),
        "end_day": window.end.date().isoformat(),
    }


# Each metric maps to its own query builder — a registry, not a switch (OCP): a new metric is a
# new entry, not an edited conditional.
_TIMESERIES_QUERIES: dict[
    TimeseriesMetric, Callable[[DateWindow], tuple[str, dict[str, object]]]
] = {
    TimeseriesMetric.SIGNUPS: _signups_query,
    TimeseriesMetric.BOOKINGS: _bookings_query,
    TimeseriesMetric.NEW_CUSTOMERS: _new_customers_query,
    TimeseriesMetric.REPLIES: _replies_query,
    TimeseriesMetric.LLM_USAGE: _llm_usage_query,
}


class SqlPlatformTimeseriesRepository:
    """One daily-bucketed metric over a UTC window, across all tenants (ADR-0012)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def daily(self, metric: TimeseriesMetric, window: DateWindow) -> list[DailyCount]:
        sql, params = _TIMESERIES_QUERIES[metric](window)
        async with self._sf() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [DailyCount(row.day, int(row.n)) for row in rows]


# Whitelist of sortable columns/aliases — never interpolate a client value into ORDER BY.
_DIRECTORY_ORDER: dict[DirectorySort, str] = {
    DirectorySort.NAME: "b.name",
    DirectorySort.SIGNUP_DATE: "created_at",
    DirectorySort.APPOINTMENTS: "appt_total",
    DirectorySort.CUSTOMERS: "customer_count",
    DirectorySort.REPLIES: "replies",
    DirectorySort.LAST_ACTIVITY: "last_activity",
}

_DIRECTORY_SQL = """
SELECT b.id, b.name, b.locale, b.timezone, a.created_at AS created_at,
  (SELECT count(*) FROM service s WHERE s.business_id = b.id) AS service_count,
  (SELECT count(*) FROM customer c WHERE c.business_id = b.id) AS customer_count,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id) AS appt_total,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id AND ap.status = :pending)
    AS ap_pending,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id AND ap.status = :confirmed)
    AS ap_confirmed,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id AND ap.status = :completed)
    AS ap_completed,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id AND ap.status = :cancelled)
    AS ap_cancelled,
  (SELECT count(*) FROM appointment ap WHERE ap.business_id = b.id AND ap.status = :no_show)
    AS ap_no_show,
  (SELECT count(*) FROM message m WHERE m.business_id = b.id AND m.role = :assistant) AS replies,
  (SELECT max(at) FROM message m WHERE m.business_id = b.id) AS last_activity,
  EXISTS (SELECT 1 FROM telegram_bot t WHERE t.business_id = b.id) AS bot_connected,
  COALESCE((SELECT mode FROM llm_config l WHERE l.business_id = b.id), 'default') AS llm_mode,
  EXISTS (SELECT 1 FROM owner_telegram_link o WHERE o.business_id = b.id) AS owner_linked
FROM business b
LEFT JOIN account a ON a.business_id = b.id
WHERE (:search = '' OR b.name ILIKE :like)
ORDER BY {order_by}
LIMIT :limit OFFSET :offset
"""

_DIRECTORY_COUNT_SQL = "SELECT count(*) FROM business b WHERE (:search = '' OR b.name ILIKE :like)"


def _to_summary(row: Row) -> BusinessSummary:
    return BusinessSummary(
        business_id=row.id,
        name=row.name,
        locale=row.locale,
        timezone=row.timezone,
        created_at=row.created_at,
        service_count=row.service_count,
        customer_count=row.customer_count,
        appointments=_appointment_counts(row),
        agent_reply_count=row.replies,
        last_activity_at=row.last_activity,
        bot_connected=row.bot_connected,
        uses_own_llm=row.llm_mode == _OWN_LLM,
        owner_telegram_linked=row.owner_linked,
    )


class SqlBusinessDirectoryRepository:
    """A sorted, searched, paginated page of per-business rollups (ADR-0012)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def page(self, query: DirectoryQuery) -> tuple[list[BusinessSummary], int]:
        # NULLS FIRST/LAST mirrors the in-memory fake, which sorts a missing value as -inf.
        direction = "DESC NULLS LAST" if query.descending else "ASC NULLS FIRST"
        order_by = f"{_DIRECTORY_ORDER[query.sort]} {direction}"
        search = query.search.strip()
        like = f"%{search}%"
        params: dict[str, object] = {
            "search": search,
            "like": like,
            "assistant": MessageRole.ASSISTANT.value,
            "limit": query.limit,
            "offset": query.offset,
            **_status_params(),
        }
        async with self._sf() as session:
            rows = (
                await session.execute(text(_DIRECTORY_SQL.format(order_by=order_by)), params)
            ).all()
            total = (
                await session.execute(text(_DIRECTORY_COUNT_SQL), {"search": search, "like": like})
            ).scalar_one()
        return [_to_summary(row) for row in rows], int(total)
