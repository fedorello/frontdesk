"""In-memory fakes for every port — used by tests and the runnable demos.

Each fake is a real, working implementation backed by dicts/lists, not a mock.
They satisfy the same port contracts the real adapters will.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from frontdesk.application.ports import (
    Account,
    Clock,
    Completion,
    Decision,
    DomainEvent,
    IdGenerator,
    LlmConfig,
    OutboundMessage,
    RecentMessage,
    ReplyClaim,
    SensitiveAction,
    ServiceRepository,
    TelegramBotConfig,
)
from frontdesk.domain.availability import ensure_bookable, free_slots
from frontdesk.domain.enums import AppointmentStatus, Channel, ReminderStatus
from frontdesk.domain.errors import AppointmentNotFound, DoubleBooking, ServiceNotFound
from frontdesk.domain.ids import (
    AccountId,
    AppointmentId,
    BusinessId,
    CustomerId,
    LinkCode,
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
    WorkingHours,
    initial_appointment_status,
)
from frontdesk.domain.notifications import OwnerTelegramLink, TelegramLinkCode


class InMemoryTelegramBotRepository:
    def __init__(self) -> None:
        self._by_business: dict[BusinessId, TelegramBotConfig] = {}

    async def get(self, business_id: BusinessId) -> TelegramBotConfig | None:
        return self._by_business.get(business_id)

    async def upsert(self, config: TelegramBotConfig) -> None:
        self._by_business[config.business_id] = config

    async def list_polling(self) -> list[TelegramBotConfig]:
        return [config for config in self._by_business.values() if not config.webhook_set]

    async def set_offset(self, business_id: BusinessId, last_update_id: int) -> None:
        bot = self._by_business.get(business_id)
        if bot is not None:
            self._by_business[business_id] = replace(bot, last_update_id=last_update_id)


class InMemoryLlmConfigRepository:
    def __init__(self) -> None:
        self._by_business: dict[BusinessId, LlmConfig] = {}

    async def get(self, business_id: BusinessId) -> LlmConfig | None:
        return self._by_business.get(business_id)

    async def upsert(self, config: LlmConfig) -> None:
        self._by_business[config.business_id] = config


class InMemoryMessaging:
    def __init__(self) -> None:
        self.sent: list[tuple[Customer, OutboundMessage]] = []

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        self.sent.append((customer, message))


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


class InMemoryIdempotency:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def seen(self, key: str) -> bool:
        if key in self._seen:
            return True
        self._seen.add(key)
        return False


class ScriptedLlmProvider:
    """Replays a fixed list of completions so the assistant loop is deterministic."""

    def __init__(self, completions: Sequence[Completion]) -> None:
        self._completions = list(completions)
        self.calls = 0
        self.last_system = ""  # captured for assertions on the prompt
        self.last_messages: list[Message] = []  # captured for assertions on the history
        self.tool_choices: list[str | None] = []  # captured per call for assertions

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[object],
        tool_choice: str | None = None,
    ) -> Completion:
        self.last_system = system
        self.last_messages = list(messages)
        self.tool_choices.append(tool_choice)
        if self.calls >= len(self._completions):
            raise IndexError("scripted provider exhausted")
        completion = self._completions[self.calls]
        self.calls += 1
        return completion


class InMemoryOwnerTelegramLinkRepository:
    def __init__(self) -> None:
        self._by_business: dict[BusinessId, OwnerTelegramLink] = {}

    async def get(self, business_id: BusinessId) -> OwnerTelegramLink | None:
        return self._by_business.get(business_id)

    async def upsert(self, link: OwnerTelegramLink) -> None:
        self._by_business[link.business_id] = link

    async def remove(self, business_id: BusinessId) -> None:
        self._by_business.pop(business_id, None)


class InMemoryTelegramLinkCodeStore:
    def __init__(self) -> None:
        self._by_code: dict[LinkCode, TelegramLinkCode] = {}

    async def issue(self, code: TelegramLinkCode) -> None:
        self._by_code[code.code] = code

    async def get(self, code: LinkCode) -> TelegramLinkCode | None:
        return self._by_code.get(code)

    async def mark_used(self, code: LinkCode) -> bool:
        existing = self._by_code.get(code)
        if existing is None or existing.used:
            return False  # already consumed or gone — the caller lost the race
        self._by_code[code] = replace(existing, used=True)
        return True


class InMemoryOwnerNotificationSender:
    """Records owner notifications instead of calling Telegram."""

    def __init__(self) -> None:
        self.sent: list[tuple[BusinessId, str, str]] = []  # (business_id, chat_id, message)

    async def send(self, business_id: BusinessId, chat_id: str, message: str) -> None:
        self.sent.append((business_id, chat_id, message))


class InMemoryReplyClaimClassifier:
    """Supervisor fake: returns the claims whose trigger phrase appears in the message."""

    def __init__(self, triggers: dict[str, ReplyClaim] | None = None) -> None:
        self._triggers = {phrase.lower(): claim for phrase, claim in (triggers or {}).items()}
        self.seen: list[str] = []  # captured for assertions on what was classified

    async def classify(self, message: str) -> frozenset[ReplyClaim]:
        self.seen.append(message)
        lowered = message.lower()
        return frozenset(claim for phrase, claim in self._triggers.items() if phrase in lowered)


class InMemoryBusinessRepository:
    def __init__(
        self,
        businesses: Sequence[Business],
        bindings: Mapping[tuple[Channel, str], BusinessId],
    ) -> None:
        self._by_id = {business.id: business for business in businesses}
        self._bindings = dict(bindings)

    async def for_channel(self, channel: Channel, to_address: str) -> Business | None:
        business_id = self._bindings.get((channel, to_address))
        if business_id is None:
            return None
        return self._by_id.get(business_id)

    async def get(self, business_id: BusinessId) -> Business:
        return self._by_id[business_id]

    async def find(self, business_id: BusinessId) -> Business | None:
        return self._by_id.get(business_id)

    async def upsert(self, business: Business) -> None:
        self._by_id[business.id] = business


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self._by_id: dict[AccountId, Account] = {}
        self._by_email: dict[str, Account] = {}

    async def by_email(self, email: str) -> Account | None:
        return self._by_email.get(email)

    async def get(self, account_id: AccountId) -> Account | None:
        return self._by_id.get(account_id)

    async def upsert(self, account: Account) -> None:
        self._by_id[account.id] = account
        self._by_email[account.email] = account


class InMemoryUsageStore:
    def __init__(self) -> None:
        self._counts: dict[tuple[BusinessId, str], int] = {}

    async def increment_and_count(self, business_id: BusinessId, day: str) -> int:
        key = (business_id, day)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def count(self, business_id: BusinessId, day: str) -> int:
        return self._counts.get((business_id, day), 0)


class InMemoryChannelBindingRepository:
    """Writes bindings into a business repo so ``for_channel`` resolves them."""

    def __init__(self, business_repo: InMemoryBusinessRepository) -> None:
        self._repo = business_repo

    async def upsert(self, channel: Channel, address: str, business_id: BusinessId) -> None:
        self._repo._bindings[(channel, address)] = business_id

    async def remove(self, channel: Channel, address: str) -> None:
        self._repo._bindings.pop((channel, address), None)


class InMemoryCustomerRepository:
    def __init__(self, ids: IdGenerator) -> None:
        self._ids = ids
        self._by_key: dict[tuple[BusinessId, Channel, str], Customer] = {}
        self._by_id: dict[CustomerId, Customer] = {}

    async def upsert(
        self, business_id: BusinessId, channel: Channel, address: str, name: str | None = None
    ) -> Customer:
        key = (business_id, channel, address)
        existing = self._by_key.get(key)
        if existing is not None:
            if name and name != existing.name:  # keep the display name fresh
                existing = replace(existing, name=name)
                self._by_key[key] = existing
                self._by_id[existing.id] = existing
            return existing
        customer = Customer(CustomerId(self._ids.new()), business_id, channel, address, name)
        self._by_key[key] = customer
        self._by_id[customer.id] = customer
        return customer

    async def get(self, customer_id: CustomerId) -> Customer:
        return self._by_id[customer_id]

    async def set_handled(self, customer_id: CustomerId, handled: bool) -> None:
        customer = replace(self._by_id[customer_id], handled_by_owner=handled)
        self._by_id[customer.id] = customer
        self._by_key[(customer.business_id, customer.channel, customer.channel_address)] = customer


class InMemoryServiceRepository:
    def __init__(self, services: Sequence[Service]) -> None:
        self._by_id = {service.id: service for service in services}

    async def get(self, service_id: ServiceId) -> Service:
        try:
            return self._by_id[service_id]
        except KeyError:
            raise ServiceNotFound(str(service_id)) from None

    async def by_name(self, business_id: BusinessId, name: str) -> Service | None:
        for service in self._by_id.values():
            if service.business_id == business_id and service.name.casefold() == name.casefold():
                return service
        return None

    async def for_business(self, business_id: BusinessId) -> list[Service]:
        return [s for s in self._by_id.values() if s.business_id == business_id]

    async def upsert(self, service: Service) -> None:
        existing = self._by_id.get(service.id)
        if existing is not None and existing.business_id != service.business_id:
            return  # tenant guard: don't overwrite another business's service (matches SQL)
        self._by_id[service.id] = service

    async def remove(self, service_id: ServiceId, business_id: BusinessId) -> None:
        service = self._by_id.get(service_id)
        if service is not None and service.business_id == business_id:
            del self._by_id[service_id]


class InMemoryResourceRepository:
    def __init__(self, resources: Sequence[Resource] = ()) -> None:
        self._by_id = {resource.id: resource for resource in resources}

    async def for_business(self, business_id: BusinessId) -> list[Resource]:
        return [r for r in self._by_id.values() if r.business_id == business_id]

    async def upsert(self, resource: Resource) -> None:
        existing = self._by_id.get(resource.id)
        if existing is not None and existing.business_id != resource.business_id:
            return  # tenant guard: don't overwrite another business's resource (matches SQL)
        self._by_id[resource.id] = resource

    async def remove(self, resource_id: ResourceId, business_id: BusinessId) -> None:
        resource = self._by_id.get(resource_id)
        if resource is not None and resource.business_id == business_id:
            del self._by_id[resource_id]


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._by_customer: dict[CustomerId, list[Message]] = {}
        self._all: list[tuple[Customer, Message]] = []

    async def history(self, customer: Customer, *, limit: int = 30) -> list[Message]:
        return self._by_customer.get(customer.id, [])[-limit:]

    async def append(self, customer: Customer, message: Message) -> None:
        self._by_customer.setdefault(customer.id, []).append(message)
        self._all.append((customer, message))

    async def recent_for_business(
        self, business_id: BusinessId, *, limit: int = 30
    ) -> list[RecentMessage]:
        recent = [(c, m) for c, m in self._all if c.business_id == business_id][-limit:]
        return [
            RecentMessage(
                c.channel_address,
                m.role.value,
                m.text,
                m.at,
                customer_id=str(c.id),
                handled=c.handled_by_owner,
                customer_name=c.name,
            )
            for c, m in reversed(recent)
        ]


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self.appointments: dict[AppointmentId, Appointment] = {}

    async def get(self, appointment_id: AppointmentId) -> Appointment:
        try:
            return self.appointments[appointment_id]
        except KeyError:
            raise AppointmentNotFound(str(appointment_id)) from None

    async def for_business(self, business_id: BusinessId) -> list[Appointment]:
        return sorted(
            (a for a in self.appointments.values() if a.business_id == business_id),
            key=lambda a: a.slot.starts_at,
        )


class InMemoryReminderStore:
    def __init__(self) -> None:
        self.reminders: dict[ReminderId, Reminder] = {}

    async def schedule(self, reminders: Sequence[Reminder]) -> None:
        for reminder in reminders:
            self.reminders[reminder.id] = reminder

    async def cancel_for(self, appointment_id: AppointmentId) -> None:
        for reminder_id, reminder in list(self.reminders.items()):
            if (
                reminder.appointment_id == appointment_id
                and reminder.status == ReminderStatus.PENDING
            ):
                self.reminders[reminder_id] = replace(reminder, status=ReminderStatus.CANCELLED)

    async def claim_due(self, now: datetime, *, limit: int = 100) -> list[Reminder]:
        due = [
            reminder
            for reminder in self.reminders.values()
            if reminder.status == ReminderStatus.PENDING and reminder.due_at <= now
        ]
        return sorted(due, key=lambda reminder: reminder.due_at)[:limit]

    async def mark_sent(self, reminder_id: ReminderId) -> None:
        reminder = self.reminders[reminder_id]
        self.reminders[reminder_id] = replace(reminder, status=ReminderStatus.SENT)


class InMemoryCalendar:
    """Availability + bookings over the domain rules, sharing an appointment store."""

    def __init__(
        self,
        business: Business,
        resources: Sequence[Resource],
        clock: Clock,
        ids: IdGenerator,
        appointments: InMemoryAppointmentRepository,
        services: ServiceRepository,
    ) -> None:
        self._business = business
        self._resources = {resource.id: resource for resource in resources}
        self._clock = clock
        self._ids = ids
        self._store = appointments
        # Needed only to re-validate a reschedule against the service's own schedule.
        self._services = services

    def _busy(
        self, resource_id: ResourceId, *, ignore: AppointmentId | None = None
    ) -> list[TimeSlot]:
        return [
            appointment.slot
            for appointment in self._store.appointments.values()
            if appointment.resource_id == resource_id
            and appointment.status != AppointmentStatus.CANCELLED
            and appointment.id != ignore
        ]

    def _reject_overlap(
        self,
        service: Service,
        working_hours: Sequence[WorkingHours],
        slot: TimeSlot,
        busy: Sequence[TimeSlot],
    ) -> None:
        buffer = timedelta(minutes=self._business.buffer_minutes)
        for taken in busy:
            if slot.overlaps(TimeSlot(taken.starts_at - buffer, taken.ends_at + buffer)):
                raise DoubleBooking("the resource is already booked for that time")
        ensure_bookable(
            business=self._business,
            working_hours=working_hours,  # the group's schedule, not the service's
            busy=[],
            slot=slot,
            now=self._clock.now(),
            max_advance_days=service.max_advance_days,
        )

    async def find_availability(
        self, service: Service, around: datetime, *, limit: int = 5
    ) -> list[TimeSlot]:
        group = self._resources[service.resource_ids[0]]
        return free_slots(
            business=self._business,
            working_hours=group.working_hours,  # availability uses the group's schedule
            busy=self._busy(group.id),
            duration_minutes=service.duration_minutes,
            now=self._clock.now(),
            around=around,
            max_advance_days=service.max_advance_days,
            limit=limit,
        )

    async def book(
        self,
        service: Service,
        resource_id: ResourceId,
        customer: Customer,
        slot: TimeSlot,
        intake: tuple[IntakeAnswer, ...] = (),
    ) -> Appointment:
        group = self._resources[resource_id]
        self._reject_overlap(service, group.working_hours, slot, self._busy(resource_id))
        appointment = Appointment(
            AppointmentId(self._ids.new()),
            self._business.id,
            service.id,
            resource_id,
            customer.id,
            slot,
            status=initial_appointment_status(service),
            intake=intake,
        )
        self._store.appointments[appointment.id] = appointment
        return appointment

    async def move(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment:
        appointment = self._store.appointments[appointment_id]
        service = await self._services.get(appointment.service_id)
        group = self._resources[appointment.resource_id]
        self._reject_overlap(
            service,
            group.working_hours,
            slot,
            self._busy(appointment.resource_id, ignore=appointment_id),
        )
        moved = replace(appointment, slot=slot)
        self._store.appointments[appointment_id] = moved
        return moved

    async def cancel(self, appointment_id: AppointmentId) -> Appointment:
        appointment = self._store.appointments[appointment_id]
        cancelled = replace(appointment, status=AppointmentStatus.CANCELLED)
        self._store.appointments[appointment_id] = cancelled
        return cancelled

    async def confirm(self, appointment_id: AppointmentId) -> Appointment:
        confirmed = self._store.appointments[appointment_id].confirmed()
        self._store.appointments[appointment_id] = confirmed
        return confirmed


class AutoDecisionGate:
    """An approval gate that always returns the same decision (for tests/demos)."""

    def __init__(self, *, approved: bool) -> None:
        self._approved = approved

    async def guard(self, action: SensitiveAction) -> Decision:
        return Decision(approved=self._approved, reason=None if self._approved else "auto-rejected")
