"""The ports (Protocols) the application depends on, and the DTOs they carry.

Adapters in ``infrastructure`` implement these; tests use in-memory fakes.
Adding an adapter never touches the core. See docs/design/contracts.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
)
from frontdesk.domain.models import (
    Appointment,
    Business,
    Customer,
    Message,
    Reminder,
    Service,
    TimeSlot,
)

# --------------------------------------------------------------------------- #
# DTOs                                                                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    text: str
    buttons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InboundMessage:
    channel: Channel
    channel_address: str
    text: str
    received_at: datetime
    provider_message_id: str


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, object]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, object]


@dataclass(frozen=True, slots=True)
class Completion:
    text: str | None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True, slots=True)
class SensitiveAction:
    tool_name: str
    args: dict[str, object]
    summary: str


@dataclass(frozen=True, slots=True)
class Decision:
    approved: bool
    edited_args: dict[str, object] | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class DomainEvent:
    business_id: BusinessId


@dataclass(frozen=True, slots=True)
class MessageReceived(DomainEvent):
    customer_id: CustomerId
    text: str


@dataclass(frozen=True, slots=True)
class AppointmentBooked(DomainEvent):
    appointment_id: AppointmentId


@dataclass(frozen=True, slots=True)
class AppointmentCancelled(DomainEvent):
    appointment_id: AppointmentId


@dataclass(frozen=True, slots=True)
class Escalated(DomainEvent):
    customer_id: CustomerId
    reason: str


@dataclass(frozen=True, slots=True)
class ApprovalRequested(DomainEvent):
    summary: str


# --------------------------------------------------------------------------- #
# Cross-cutting ports                                                          #
# --------------------------------------------------------------------------- #


class Clock(Protocol):
    def now(self) -> datetime: ...  # UTC


class IdGenerator(Protocol):
    def new(self) -> str: ...


# --------------------------------------------------------------------------- #
# Driven ports                                                                #
# --------------------------------------------------------------------------- #


class MessagingPort(Protocol):
    async def send(self, customer: Customer, message: OutboundMessage) -> None: ...


class LlmProvider(Protocol):
    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
    ) -> Completion: ...


class Calendar(Protocol):
    async def find_availability(
        self, service: Service, around: datetime, *, limit: int = 5
    ) -> list[TimeSlot]: ...
    async def book(
        self,
        service: Service,
        resource_id: ResourceId,
        customer: Customer,
        slot: TimeSlot,
    ) -> Appointment: ...
    async def move(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment: ...
    async def cancel(self, appointment_id: AppointmentId) -> Appointment: ...


class BusinessRepository(Protocol):
    async def for_channel(self, channel: Channel, to_address: str) -> Business | None: ...
    async def get(self, business_id: BusinessId) -> Business: ...


class CustomerRepository(Protocol):
    async def upsert(self, business_id: BusinessId, channel: Channel, address: str) -> Customer: ...


class ConversationRepository(Protocol):
    async def history(self, customer: Customer, *, limit: int = 30) -> list[Message]: ...
    async def append(self, customer: Customer, message: Message) -> None: ...


class AppointmentRepository(Protocol):
    async def get(self, appointment_id: AppointmentId) -> Appointment: ...


class ReminderStore(Protocol):
    async def schedule(self, reminders: Sequence[Reminder]) -> None: ...
    async def cancel_for(self, appointment_id: AppointmentId) -> None: ...
    async def claim_due(self, now: datetime, *, limit: int = 100) -> list[Reminder]: ...
    async def mark_sent(self, reminder_id: ReminderId) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class ApprovalGate(Protocol):
    async def guard(self, action: SensitiveAction) -> Decision: ...
