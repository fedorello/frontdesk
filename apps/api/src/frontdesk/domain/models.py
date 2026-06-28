"""Value objects and entities. Frozen, validated, pure (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time

from .enums import AppointmentStatus, Channel, MessageRole, ReminderStatus
from .errors import InvalidTransition
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


MAX_INTAKE_FIELDS = 5


@dataclass(frozen=True, slots=True)
class IntakeField:
    """One piece of info to collect from the customer before booking a service."""

    name: str  # e.g. "Birth date"
    description: str = ""  # what it is — guides the assistant
    ask: str = ""  # optional: how to phrase the question to the customer


@dataclass(frozen=True, slots=True)
class IntakeAnswer:
    """The customer's answer to one IntakeField, stored on the appointment."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class Service:
    id: ServiceId
    business_id: BusinessId
    name: str
    duration_minutes: int
    price: Money | None = None
    resource_ids: tuple[ResourceId, ...] = ()  # the single group this service belongs to
    description: str = ""  # what the service is — given to the assistant and shown to owners
    max_advance_days: int = 30  # how far ahead a customer may book this service
    intake_fields: tuple[IntakeField, ...] = ()  # info to collect before booking
    requires_confirmation: bool = False  # if True, bookings stay pending until the owner confirms

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.max_advance_days <= 0:
            raise ValueError("max_advance_days must be positive")
        if len(self.intake_fields) > MAX_INTAKE_FIELDS:
            raise ValueError(f"at most {MAX_INTAKE_FIELDS} intake fields")


@dataclass(frozen=True, slots=True)
class Resource:
    """A service group: one specialist/calendar that owns a weekly schedule.

    Services in the same group share this schedule and one booking calendar (the
    ``no_double_book`` exclusion constraint keys on the group), so they can't overlap.
    Services in different groups are independent. See docs/SERVICE_GROUPS.md.
    """

    id: ResourceId
    business_id: BusinessId
    name: str
    working_hours: tuple[WorkingHours, ...] = ()


# The starter schedule a new business's default group gets: weekdays 09:00-17:00.
DEFAULT_GROUP_HOURS = tuple(WorkingHours(weekday, time(9), time(17)) for weekday in range(5))
DEFAULT_GROUP_NAME = "Main"


def default_group(business_id: BusinessId, group_id: ResourceId) -> Resource:
    """A starter group so every business has one calendar from the moment it's created."""
    return Resource(group_id, business_id, DEFAULT_GROUP_NAME, DEFAULT_GROUP_HOURS)


@dataclass(frozen=True, slots=True)
class Business:
    id: BusinessId
    name: str
    timezone: str  # IANA, e.g. "America/Montevideo"
    lead_time_minutes: int = 0
    buffer_minutes: int = 0
    knowledge: tuple[KnowledgeItem, ...] = ()
    description: str = ""  # one free-text "about us" injected into every assistant prompt
    address: str = ""  # where the business is (ignored when `online` is set)
    online: bool = False  # the business operates online — there is no physical address
    locale: str = "en"  # the owner's chosen language; the bot's filler phrases use it
    owner_name: str = ""  # the owner's display name, shown to customers when the owner replies

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
    handled_by_owner: bool = False  # the owner has taken over; the assistant stays silent


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
    intake: tuple[IntakeAnswer, ...] = ()  # the customer's answers to the service's intake fields

    def confirmed(self) -> Appointment:
        """Return this appointment marked confirmed.

        Idempotent: confirming an already-confirmed appointment is a no-op.
        Raises InvalidTransition for a cancelled or completed appointment.
        """
        if self.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            raise InvalidTransition(f"cannot confirm a {self.status.value} appointment")
        return replace(self, status=AppointmentStatus.CONFIRMED)


def initial_appointment_status(service: Service) -> AppointmentStatus:
    """A booking is confirmed on creation unless the service requires manual confirmation."""
    return (
        AppointmentStatus.PENDING if service.requires_confirmation else AppointmentStatus.CONFIRMED
    )


@dataclass(frozen=True, slots=True)
class Reminder:
    id: ReminderId
    business_id: BusinessId
    appointment_id: AppointmentId
    due_at: datetime
    kind: str
    status: ReminderStatus = ReminderStatus.PENDING
