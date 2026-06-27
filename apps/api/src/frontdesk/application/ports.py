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
    AccountId,
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import (
    Appointment,
    Business,
    Customer,
    IntakeAnswer,
    Message,
    Reminder,
    Resource,
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
    from_address: str  # the customer's address (phone / chat id)
    to_address: str  # the business's channel binding that received it
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


class Random(Protocol):
    """Source of randomness, injected so e.g. phrase selection is deterministic in tests."""

    def choice(self, items: Sequence[str]) -> str: ...


class SecretCipher(Protocol):
    """Encrypts secrets (API/bot keys) for storage at rest. See ADR-0009."""

    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, token: str) -> str: ...


class Idempotency(Protocol):
    async def seen(self, key: str) -> bool:
        """True if ``key`` was already processed; records it as processed."""
        ...


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
        intake: tuple[IntakeAnswer, ...] = (),
    ) -> Appointment: ...
    async def move(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment: ...
    async def cancel(self, appointment_id: AppointmentId) -> Appointment: ...


class BusinessRepository(Protocol):
    async def for_channel(self, channel: Channel, to_address: str) -> Business | None: ...
    async def get(self, business_id: BusinessId) -> Business: ...
    async def find(self, business_id: BusinessId) -> Business | None: ...
    async def upsert(self, business: Business) -> None: ...


class ChannelBindingRepository(Protocol):
    async def upsert(self, channel: Channel, address: str, business_id: BusinessId) -> None: ...
    async def remove(self, channel: Channel, address: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Account:
    id: AccountId
    email: str
    password_hash: str
    business_id: BusinessId | None = None


class AccountRepository(Protocol):
    async def by_email(self, email: str) -> Account | None: ...
    async def get(self, account_id: AccountId) -> Account | None: ...
    async def upsert(self, account: Account) -> None: ...


class UsageStore(Protocol):
    """Per-business daily usage counter for the managed-default LLM (cost control)."""

    async def increment_and_count(self, business_id: BusinessId, day: str) -> int: ...
    async def count(self, business_id: BusinessId, day: str) -> int: ...


class CustomerRepository(Protocol):
    async def upsert(self, business_id: BusinessId, channel: Channel, address: str) -> Customer: ...
    async def get(self, customer_id: CustomerId) -> Customer: ...


class ServiceRepository(Protocol):
    async def get(self, service_id: ServiceId) -> Service: ...
    async def by_name(self, business_id: BusinessId, name: str) -> Service | None: ...
    async def for_business(self, business_id: BusinessId) -> list[Service]: ...
    async def upsert(self, service: Service) -> None: ...
    async def remove(self, service_id: ServiceId) -> None: ...


class ResourceRepository(Protocol):
    async def for_business(self, business_id: BusinessId) -> list[Resource]: ...
    async def upsert(self, resource: Resource) -> None: ...


@dataclass(frozen=True, slots=True)
class RecentMessage:
    customer: str  # the customer's channel address
    role: str
    text: str
    at: datetime


class ConversationRepository(Protocol):
    async def history(self, customer: Customer, *, limit: int = 30) -> list[Message]: ...
    async def append(self, customer: Customer, message: Message) -> None: ...
    async def recent_for_business(
        self, business_id: BusinessId, *, limit: int = 30
    ) -> list[RecentMessage]: ...


class AppointmentRepository(Protocol):
    async def get(self, appointment_id: AppointmentId) -> Appointment: ...
    async def for_business(self, business_id: BusinessId) -> list[Appointment]: ...


@dataclass(frozen=True, slots=True)
class TelegramBotConfig:
    business_id: BusinessId
    bot_token: str
    secret_token: str
    username: str
    webhook_set: bool = False
    last_update_id: int = 0  # the poller's getUpdates offset cursor


class TelegramBotRepository(Protocol):
    async def get(self, business_id: BusinessId) -> TelegramBotConfig | None: ...
    async def upsert(self, config: TelegramBotConfig) -> None: ...
    async def list_connected(self) -> list[TelegramBotConfig]: ...
    async def set_offset(self, business_id: BusinessId, last_update_id: int) -> None: ...


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """A business's LLM provider — the platform default, or its own key.

    ``api_key`` is plaintext in memory; the SQL adapter encrypts it at rest and only
    ever exposes ``api_key_hint`` (the last few characters). See ADR-0009.
    """

    business_id: BusinessId
    mode: str  # "default" | "own"
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_key_hint: str | None = None


class LlmConfigRepository(Protocol):
    async def get(self, business_id: BusinessId) -> LlmConfig | None: ...
    async def upsert(self, config: LlmConfig) -> None: ...


class AssistantObserver(Protocol):
    """Notified of the assistant's interim reasoning and each tool call.

    A no-op by default; the web chat uses it to surface the agent's steps.
    """

    async def on_thought(self, text: str) -> None: ...
    async def on_tool(self, name: str, args: dict[str, object], result: str) -> None: ...


class ReminderStore(Protocol):
    async def schedule(self, reminders: Sequence[Reminder]) -> None: ...
    async def cancel_for(self, appointment_id: AppointmentId) -> None: ...
    async def claim_due(self, now: datetime, *, limit: int = 100) -> list[Reminder]: ...
    async def mark_sent(self, reminder_id: ReminderId) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class ApprovalGate(Protocol):
    async def guard(self, action: SensitiveAction) -> Decision: ...
