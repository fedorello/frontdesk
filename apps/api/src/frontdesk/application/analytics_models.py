"""Read models for the platform analytics dashboard (ADR-0012).

Frozen, slotted value objects that carry shaped numbers across the analytics ports and
out of the use case. They hold counts and aggregates only — never customer PII — which is
how the privacy boundary of ADR-0012 is enforced structurally rather than by convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TimeseriesMetric(StrEnum):
    """A daily-bucketed metric the dashboard can chart over a window."""

    SIGNUPS = "signups"  # accounts created per day
    BOOKINGS = "bookings"  # appointments created per day
    REPLIES = "replies"  # assistant messages sent per day
    NEW_CUSTOMERS = "new_customers"  # customers created per day
    LLM_USAGE = "llm_usage"  # managed-default LLM calls per day


class DirectorySort(StrEnum):
    """Which column the business directory is ordered by."""

    NAME = "name"
    SIGNUP_DATE = "signup_date"
    APPOINTMENTS = "appointments"
    CUSTOMERS = "customers"
    REPLIES = "replies"
    LAST_ACTIVITY = "last_activity"


@dataclass(frozen=True, slots=True)
class DateWindow:
    """A half-open UTC time range ``[start, end)`` for a time-series query."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("DateWindow bounds must be timezone-aware (UTC)")
        if self.end <= self.start:
            raise ValueError("end must be after start")


@dataclass(frozen=True, slots=True)
class DailyCount:
    """One point in a time series: a UTC day and its count."""

    day: date
    count: int


@dataclass(frozen=True, slots=True)
class SignupCounts:
    """New accounts in rolling windows ending now."""

    today: int
    last_7_days: int
    last_30_days: int


@dataclass(frozen=True, slots=True)
class AppointmentStatusCounts:
    """Appointment counts split by status."""

    pending: int
    confirmed: int
    completed: int
    cancelled: int
    no_show: int

    @property
    def total(self) -> int:
        return self.pending + self.confirmed + self.completed + self.cancelled + self.no_show


@dataclass(frozen=True, slots=True)
class LlmModeCounts:
    """How many businesses are on the managed default vs their own LLM key."""

    default: int
    own: int


@dataclass(frozen=True, slots=True)
class PlatformTotals:
    """The headline counts across all tenants at one instant."""

    total_businesses: int
    signups: SignupCounts
    active_businesses_30d: int
    total_customers: int
    total_agent_replies: int
    appointments: AppointmentStatusCounts
    telegram_bots_connected: int
    owner_telegram_links: int
    llm_modes: LlmModeCounts
    pending_approvals: int


@dataclass(frozen=True, slots=True)
class ActivationFunnel:
    """How many businesses reached each onboarding stage (each stage a count of businesses)."""

    signed_up: int
    connected_channel: int
    received_message: int
    booked_appointment: int


@dataclass(frozen=True, slots=True)
class FunnelConversion:
    """Funnel stage reach as a fraction of signed-up businesses (0.0 to 1.0)."""

    connected_pct: float
    received_message_pct: float
    booked_pct: float


@dataclass(frozen=True, slots=True)
class Overview:
    """The assembled operator overview: raw totals + funnel + derived rates."""

    totals: PlatformTotals
    funnel: ActivationFunnel
    funnel_conversion: FunnelConversion
    no_show_rate: float
    cancellation_rate: float


@dataclass(frozen=True, slots=True)
class DirectoryQuery:
    """One page of the business directory listing, with its filters."""

    limit: int
    offset: int
    sort: DirectorySort
    descending: bool
    search: str


@dataclass(frozen=True, slots=True)
class BusinessSummary:
    """One business's rollup for the directory table — counts and config only, no PII."""

    business_id: str
    name: str
    locale: str
    timezone: str
    created_at: datetime
    service_count: int
    customer_count: int
    appointments: AppointmentStatusCounts
    agent_reply_count: int
    last_activity_at: datetime | None
    bot_connected: bool
    uses_own_llm: bool
    owner_telegram_linked: bool
