"""Value objects and entities. Frozen, validated, pure (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from .enums import AppointmentStatus, Channel, MessageRole, ReminderStatus
from .ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from .money import Money

_LAST_WEEKDAY = 6  # Sunday, with Monday = 0


@dataclass(frozen=True, slots=True)
class TimeSlot:
    """A half-open time range ``[starts_at, ends_at)`` in UTC."""

    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")

    @property
    def duration_minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    def overlaps(self, other: TimeSlot) -> bool:
        """True if the two half-open ranges intersect (touching does not count)."""
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at


@dataclass(frozen=True, slots=True)
class WorkingHours:
    """An opening window on one weekday, in the business's local timezone."""

    weekday: int  # 0 = Monday … 6 = Sunday
    opens: time
    closes: time

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= _LAST_WEEKDAY:
            raise ValueError("weekday must be in 0..6")
        if self.closes <= self.opens:
            raise ValueError("closes must be after opens")


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """One FAQ entry the assistant may answer from."""

    question: str
    answer: str


@dataclass(frozen=True, slots=True)
class Service:
    id: ServiceId
    business_id: BusinessId
    name: str
    duration_minutes: int
    price: Money | None = None
    resource_ids: tuple[ResourceId, ...] = ()
    description: str = ""  # what the service is — given to the assistant and shown to owners

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")


@dataclass(frozen=True, slots=True)
class Resource:
    id: ResourceId
    business_id: BusinessId
    name: str
    working_hours: tuple[WorkingHours, ...] = ()


@dataclass(frozen=True, slots=True)
class Business:
    id: BusinessId
    name: str
    timezone: str  # IANA, e.g. "America/Montevideo"
    lead_time_minutes: int = 0
    buffer_minutes: int = 0
    knowledge: tuple[KnowledgeItem, ...] = ()
    description: str = ""  # one free-text "about us" injected into every assistant prompt

    def __post_init__(self) -> None:
        if self.lead_time_minutes < 0:
            raise ValueError("lead_time_minutes must not be negative")
        if self.buffer_minutes < 0:
            raise ValueError("buffer_minutes must not be negative")


@dataclass(frozen=True, slots=True)
class Customer:
    id: CustomerId
    business_id: BusinessId
    channel: Channel
    channel_address: str
    name: str | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    text: str
    at: datetime
    tool_call_id: str | None = None  # set on MessageRole.TOOL results


@dataclass(frozen=True, slots=True)
class Appointment:
    id: AppointmentId
    business_id: BusinessId
    service_id: ServiceId
    resource_id: ResourceId
    customer_id: CustomerId
    slot: TimeSlot
    status: AppointmentStatus = AppointmentStatus.PENDING


@dataclass(frozen=True, slots=True)
class Reminder:
    id: ReminderId
    business_id: BusinessId
    appointment_id: AppointmentId
    due_at: datetime
    kind: str
    status: ReminderStatus = ReminderStatus.PENDING
