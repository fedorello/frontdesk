# Contracts

The precise contract the implementation must honor: domain types, ports, use
cases, the assistant's tools, the two state machines, the invariants, the
database schema, and the errors. Signatures are written in Python (the backend
language); they are the source of truth that code and tests are checked against.

## Conventions

- **Ids** are opaque strings (UUIDv7 in production, sequential in tests) wrapped in
  `NewType` per entity (`BusinessId`, `AppointmentId`, …) so they never mix.
- **Time** is always timezone-aware UTC at rest and in code; a business has an IANA
  `timezone` used only for display and for interpreting "Friday at 5".
- **Money** is integer minor units (`amount_cents: int`, `currency: str`) — never a
  float.
- **Language** is a BCP-47 tag (`"en"`, `"es"`, `"ru"`); the assistant replies in
  the customer's language.
- Every persisted entity carries `business_id` ([ADR-0003](../adr/0003-multi-tenant-by-business.md)).

## Enums

```python
class Channel(StrEnum):        # how we reach a customer
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"

class AppointmentStatus(StrEnum):
    PENDING = "pending"        # held, not yet confirmed
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"

class RiskTier(StrEnum):       # for the approval gate (ADR-0005)
    SAFE = "safe"
    SENSITIVE = "sensitive"

class MessageRole(StrEnum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"              # a tool result fed back into the loop
```

A `TOOL` message carries the result of a `ToolCall` (with its `tool_call_id`) and
re-enters `messages` so the next `complete()` sees what the tool returned.

## Value objects & entities

Imports (`datetime`/`time`, `NewType`, `dataclass`, `StrEnum`, typing) are elided.

```python
# Ids — one NewType per entity so they never mix.
BusinessId = NewType("BusinessId", str)
ServiceId = NewType("ServiceId", str)
ResourceId = NewType("ResourceId", str)
CustomerId = NewType("CustomerId", str)
AppointmentId = NewType("AppointmentId", str)
ReminderId = NewType("ReminderId", str)

@dataclass(frozen=True)
class Money:                   # persisted as price_cents + currency columns
    amount_cents: int
    currency: str              # ISO 4217, e.g. "USD"

@dataclass(frozen=True)
class KnowledgeItem:           # one FAQ entry the assistant may answer from
    question: str
    answer: str

@dataclass(frozen=True)
class WorkingHours:            # per weekday, in the business timezone
    weekday: int               # 0=Mon … 6=Sun
    opens: time                # local time
    closes: time

@dataclass(frozen=True)
class TimeSlot:
    starts_at: datetime        # UTC
    ends_at: datetime          # UTC

@dataclass(frozen=True)
class Service:
    id: ServiceId
    business_id: BusinessId
    name: str
    duration_minutes: int
    price: Money | None
    resource_ids: tuple[ResourceId, ...]   # who can perform it

@dataclass(frozen=True)
class Resource:                # a person or asset a booking consumes
    id: ResourceId
    business_id: BusinessId
    name: str
    working_hours: tuple[WorkingHours, ...]

@dataclass(frozen=True)
class Business:
    id: BusinessId
    name: str
    timezone: str              # IANA, e.g. "America/Montevideo"
    lead_time_minutes: int     # min notice before a booking
    buffer_minutes: int        # gap kept between appointments
    knowledge: tuple[KnowledgeItem, ...]    # FAQ the assistant answers from

@dataclass(frozen=True)
class Customer:
    id: CustomerId
    business_id: BusinessId
    channel: Channel
    channel_address: str       # phone number / chat id, unique per (business, channel)
    name: str | None
    language: str | None

@dataclass(frozen=True)
class Message:
    role: MessageRole
    text: str
    at: datetime
    tool_call_id: str | None = None    # set on MessageRole.TOOL results

# A Conversation is just a Customer plus its ordered Messages — there is no
# separate entity; the `conversation` table groups messages per customer.

@dataclass(frozen=True)
class Appointment:
    id: AppointmentId
    business_id: BusinessId
    service_id: ServiceId
    resource_id: ResourceId
    customer_id: CustomerId
    slot: TimeSlot
    status: AppointmentStatus

@dataclass(frozen=True)
class Reminder:
    id: ReminderId
    business_id: BusinessId
    appointment_id: AppointmentId
    due_at: datetime           # UTC
    kind: str                  # e.g. "24h", "2h"
    status: ReminderStatus
```

## Domain errors

Pure, raised by the domain/application; mapped to channel replies or HTTP at the
edge.

```python
class DomainError(Exception): ...
class SlotUnavailable(DomainError): ...        # the slot is taken or out of hours
class DoubleBooking(DomainError): ...          # resource already booked (race)
class LeadTimeViolation(DomainError): ...      # too close to now
class AppointmentNotFound(DomainError): ...
class ServiceNotFound(DomainError): ...
class TenantMismatch(DomainError): ...         # a cross-business access — a bug, must never happen
```

## Ports (application/ports)

Defined as `Protocol`s in the application layer; adapters implement them; tests use
in-memory fakes. Adding an adapter never touches the core.

```python
@dataclass(frozen=True)
class OutboundMessage:
    text: str
    buttons: tuple[str, ...] = ()      # quick replies, e.g. ("Confirm", "Reschedule")

@dataclass(frozen=True)
class InboundMessage:                   # normalized across channels
    channel: Channel
    channel_address: str
    text: str
    received_at: datetime
    provider_message_id: str            # for idempotency

class MessagingPort(Protocol):
    async def send(self, customer: Customer, message: OutboundMessage) -> None: ...

# --- LLM (model-agnostic, ADR-0006) ---
@dataclass(frozen=True)
class ToolSpec:                # a tool the model may call
    name: str
    description: str
    parameters: Mapping[str, object]    # JSON Schema for the args

@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: Mapping[str, object]

@dataclass(frozen=True)
class Completion:
    text: str | None
    tool_calls: tuple[ToolCall, ...]

class LlmProvider(Protocol):
    async def complete(
        self, *, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> Completion: ...

# --- Calendar (availability + bookings) ---
class Calendar(Protocol):
    async def find_availability(
        self, service: Service, around: datetime, *, limit: int = 5
    ) -> list[TimeSlot]: ...
    async def book(
        self, service: Service, resource_id: ResourceId, customer: Customer, slot: TimeSlot
    ) -> Appointment: ...                         # raises SlotUnavailable / DoubleBooking
    async def move(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment: ...
    async def cancel(self, appointment_id: AppointmentId) -> Appointment: ...

# --- Persistence ---
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

class ReminderStore(Protocol):                    # durable scheduler (ADR-0004)
    async def schedule(self, reminders: Sequence[Reminder]) -> None: ...
    async def cancel_for(self, appointment_id: AppointmentId) -> None: ...
    async def claim_due(self, now: datetime, *, limit: int = 100) -> list[Reminder]: ...
    async def mark_sent(self, reminder_id: ReminderId) -> None: ...

# --- Cross-cutting ---
class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

class ApprovalGate(Protocol):                     # backed by airlock-hitl (ADR-0005)
    # SensitiveAction and Decision are the airlock-hitl request / decision types.
    async def guard(self, action: SensitiveAction) -> Decision: ...

class Clock(Protocol):
    def now(self) -> datetime: ...                # UTC

class IdGenerator(Protocol):
    def new(self) -> str: ...
```

## Application use cases

```python
class HandleInboundMessage:                       # Flow 1 — the assistant loop
    async def __call__(self, inbound: InboundMessage) -> None: ...
    # resolve business (BusinessRepository.for_channel) → upsert customer →
    # load history → run the tool-use loop until the model returns text →
    # send the reply → persist the exchange → publish events.

class BookAppointment:                             # Flow 2
    async def __call__(
        self, business: Business, service: Service, resource_id: ResourceId,
        customer: Customer, slot: TimeSlot
    ) -> Appointment: ...
    # Calendar.book (transactional, rejects double-book) →
    # ReminderStore.schedule(reminders for the appointment) → publish.

class RescheduleAppointment: ...                   # Calendar.move + reschedule reminders
class CancelAppointment: ...                       # Calendar.cancel + ReminderStore.cancel_for

class SendDueReminders:                            # Flow 3 — the worker tick
    async def __call__(self, now: datetime) -> int: ...
    # ReminderStore.claim_due → MessagingPort.send (with Confirm/Reschedule) →
    # mark_sent. Returns how many were sent.
```

## The assistant's tools

What the model sees. The loop exposes exactly these; the typed core enforces the
rules ([ADR-0007](../adr/0007-assistant-as-tool-use-agent.md)). `risk` drives the
gate.

| Tool                 | Args                                  | Risk      | Effect                                  |
| -------------------- | ------------------------------------- | --------- | --------------------------------------- |
| `answer_question`    | `topic: str`                          | safe      | Reply from the business knowledge base. |
| `find_availability`  | `service, around`                     | safe      | Real free slots from the calendar.      |
| `book`               | `service, slot`                       | safe¹     | Create an appointment.                  |
| `reschedule`         | `appointment_id, slot`                | safe¹     | Move an appointment.                    |
| `cancel`             | `appointment_id`                      | safe¹     | Cancel an appointment.                  |
| `escalate`           | `reason: str`                         | safe      | Hand off to a human.                    |
| `issue_refund`       | `appointment_id, amount`              | sensitive | Refund — **passes the approval gate.**  |

¹ Booking/rescheduling/cancelling are "safe" by default (reversible, policy-bounded)
but the risk tier is **configurable per business** — a business can require approval
for any of them.

When the model calls `book` / `reschedule` / `cancel` it chooses only the
**service** and **slot**; the core binds the rest — the **customer** from the
conversation, and the **resource** auto-selected from availability. `issue_refund`'s
`amount` is a `Money`.

The assistant **never invents** prices, availability, or facts: it answers only from
the knowledge base and the real calendar, and `escalate`s when unsure.

## State machines

### Appointment

| From        | Event                | To          |
| ----------- | -------------------- | ----------- |
| —           | `book`               | `pending`   |
| `pending`   | customer confirms    | `confirmed` |
| `pending`   | reschedule           | `pending`   |
| `confirmed` | reschedule           | `confirmed` |
| `pending` / `confirmed` | cancel   | `cancelled` |
| `confirmed` | service rendered     | `completed` |
| `confirmed` | customer didn't come | `no_show`   |

`cancelled`, `completed`, `no_show` are terminal. Any other transition raises.

### Reminder

| From      | Event                            | To          |
| --------- | -------------------------------- | ----------- |
| —         | scheduled on booking / reschedule | `pending`   |
| `pending` | worker sends it                  | `sent`      |
| `pending` | appointment cancelled / moved    | `cancelled` |

`sent` and `cancelled` are terminal. A **reschedule** cancels the appointment's
pending reminders and schedules fresh `pending` ones (Invariant 4), so the
"scheduled" event fires on both booking and reschedule.

## Invariants

1. **No double-booking.** A resource has at most one non-cancelled appointment for
   any instant — enforced by a Postgres exclusion constraint **and** an application
   check.
2. **Within hours + lead time.** A booking is inside the resource's working hours
   (minus buffer) and at least `lead_time_minutes` from now.
3. **Tenant isolation.** No read or write crosses a `business_id`; `TenantMismatch`
   is a never-happens bug, asserted in tests.
4. **Reminder exactly-once.** A `pending` reminder is sent at most once
   (`FOR UPDATE SKIP LOCKED`); cancelling/moving an appointment cancels its pending
   reminders in the same transaction.
5. **Webhook idempotency.** A repeated `provider_message_id` is processed once.
6. **Grounding.** Replies use only the knowledge base and the real calendar; no
   invented facts.
7. **Gate before damage.** A `sensitive` tool does not execute until approved.

## Database schema (persistence contract)

PostgreSQL; every table has `business_id`, `created_at`, `updated_at`. Key shape and
constraints (full DDL lives in Alembic migrations):

- `business(id, name, timezone, lead_time_minutes, buffer_minutes, …)`
- `service(id, business_id→business, name, duration_minutes, price_cents, currency)`
- `resource(id, business_id→business, name)` + `resource_hours(resource_id, weekday, opens, closes)`
- `service_resource(service_id, resource_id)` — which resources perform a service
- `channel_binding(business_id, channel, address)` — unique `(channel, address)`; resolves the tenant for an inbound webhook
- `customer(id, business_id, channel, address, name, language)` — unique `(business_id, channel, address)`
- `conversation(id, business_id, customer_id)` + `message(id, conversation_id, role, text, at)`
- `appointment(id, business_id, service_id, resource_id, customer_id, starts_at, ends_at, status)`
  - `starts_at` and `ends_at` are `NOT NULL` (a NULL range bound would defeat the constraint)
  - requires `CREATE EXTENSION IF NOT EXISTS btree_gist;` — GiST needs `btree_gist` to use `=` on the scalar `resource_id` inside the constraint
  - **`EXCLUDE USING gist (resource_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status <> 'cancelled')`** — the no-double-book guarantee
- `reminder(id, business_id, appointment_id, due_at, kind, status)`
  - index `(status, due_at)` for the worker's claim query
- `processed_message(provider_message_id PRIMARY KEY, …)` — webhook idempotency

## Events (for the live dashboard)

```python
class DomainEvent: ...
class MessageReceived(DomainEvent): ...
class AppointmentBooked(DomainEvent): ...
class AppointmentCancelled(DomainEvent): ...
class Escalated(DomainEvent): ...
class ApprovalRequested(DomainEvent): ...
```

Published to Redis pub/sub; the dashboard subscribes for live updates. Events are
ephemeral — never the source of truth.

## Webhook contract

Each channel webhook (`interface`):

1. **Verifies** the provider signature/secret before any work.
2. Normalizes the payload to `InboundMessage` (channel adapter).
3. Drops duplicates by `provider_message_id` (`processed_message`).
4. Calls `HandleInboundMessage`.
5. Returns the provider's expected ack quickly; heavy work is awaited within the
   request budget or deferred.
