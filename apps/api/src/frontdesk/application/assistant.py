"""The assistant: a tool-use loop whose tools are the domain use cases.

The model decides *what* to attempt; the typed, tested core decides *whether and
how* it happens. It answers only from the knowledge base and the real calendar,
and escalates when unsure. See ADR-0007.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    RescheduleAppointment,
)
from frontdesk.application.ports import (
    AppointmentRepository,
    ApprovalGate,
    ApprovalRequested,
    AssistantObserver,
    BusinessRepository,
    Calendar,
    Clock,
    ConversationRepository,
    CustomerRepository,
    Escalated,
    EventPublisher,
    InboundMessage,
    LlmProvider,
    MessageReceived,
    MessagingPort,
    OutboundMessage,
    SensitiveAction,
    ServiceRepository,
    ToolCall,
    ToolSpec,
)
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.errors import DomainError
from frontdesk.domain.ids import AppointmentId
from frontdesk.domain.models import Business, Customer, Message, Service, TimeSlot

MAX_STEPS = 6
ESCALATION_FALLBACK = "Let me get a colleague to help you with that — they'll be in touch shortly."
SLOT_FORMAT = "%a %d %b %H:%M UTC"

ToolHandler = Callable[["Business", "Customer", dict[str, object]], Awaitable[str]]


class _NullObserver:
    async def on_thought(self, text: str) -> None: ...
    async def on_tool(self, name: str, args: dict[str, object], result: str) -> None: ...


_NULL_OBSERVER: AssistantObserver = _NullObserver()

TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "answer_question",
        "Answer a question from the business knowledge base.",
        {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
    ),
    ToolSpec(
        "find_availability",
        "List real free slots for a service. 'around' is an optional ISO datetime.",
        {
            "type": "object",
            "properties": {"service": {"type": "string"}, "around": {"type": "string"}},
            "required": ["service"],
        },
    ),
    ToolSpec(
        "book",
        "Book an appointment for a service at a slot start time (ISO).",
        {
            "type": "object",
            "properties": {"service": {"type": "string"}, "start": {"type": "string"}},
            "required": ["service", "start"],
        },
    ),
    ToolSpec(
        "reschedule",
        "Move an appointment to a new start time (ISO).",
        {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}, "start": {"type": "string"}},
            "required": ["appointment_id", "start"],
        },
    ),
    ToolSpec(
        "cancel",
        "Cancel an appointment.",
        {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}},
            "required": ["appointment_id"],
        },
    ),
    ToolSpec(
        "escalate",
        "Hand off to a human when you cannot help.",
        {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    ),
    ToolSpec(
        "issue_refund",
        "Issue a refund for an appointment. Sensitive — requires human approval.",
        {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["appointment_id"],
        },
    ),
)


@dataclass(frozen=True, slots=True)
class AssistantDeps:
    llm: LlmProvider
    businesses: BusinessRepository
    customers: CustomerRepository
    conversations: ConversationRepository
    services: ServiceRepository
    appointments: AppointmentRepository
    calendar: Calendar
    book: BookAppointment
    reschedule: RescheduleAppointment
    cancel: CancelAppointment
    messaging: MessagingPort
    events: EventPublisher
    gate: ApprovalGate
    clock: Clock


def _arg(args: dict[str, object], key: str) -> str:
    value = args.get(key)
    return value if isinstance(value, str) else ""


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _format_slots(slots: Sequence[TimeSlot]) -> str:
    if not slots:
        return "no free times right now"
    return "; ".join(
        f"{s.starts_at.strftime(SLOT_FORMAT)} (start={s.starts_at.isoformat()})" for s in slots
    )


def _menu_line(service: Service) -> str:
    line = f"- {service.name} ({service.duration_minutes} min)"
    return f"{line} — {service.description}" if service.description else line


def _location_line(business: Business) -> str:
    if business.online:
        return "\n\nThis business is online — appointments are remote; there is no address."
    if business.address:
        return f"\n\nLocation: {business.address}"
    return ""


def _system_prompt(business: Business, services: Sequence[Service]) -> str:
    menu = "\n".join(_menu_line(s) for s in services) or "- (none yet)"
    knowledge = "\n".join(f"Q: {item.question}\nA: {item.answer}" for item in business.knowledge)
    about = f"\n\nAbout {business.name}:\n{business.description}" if business.description else ""
    return (
        f"You are the front desk for {business.name}. Be brief and warm, and reply in the "
        "customer's language. Use the tools to check real availability and to book — never "
        "invent times, prices, services, or facts. Escalate when you cannot help."
        f"{about}{_location_line(business)}\n\n"
        "These are the ONLY services we offer. Never offer, suggest, or search for anything "
        f"not on this list — if a customer asks for something else, say we don't offer it:\n{menu}"
        "\n\nFree times change as time passes. Always read availability from find_availability "
        "right before offering slots, and never repeat a slot list from earlier in the chat. If a "
        "booking fails, the tool gives you the current free slots — offer exactly those."
        f"\n\nKnowledge base:\n{knowledge}"
    )


class Assistant:
    """Handles one inbound message: run the tool-use loop, reply, persist."""

    def __init__(self, deps: AssistantDeps, observer: AssistantObserver | None = None) -> None:
        self._d = deps
        self._observer = observer or _NULL_OBSERVER
        self._handlers: dict[str, ToolHandler] = {
            "answer_question": self._answer,
            "find_availability": self._find,
            "book": self._do_book,
            "reschedule": self._do_reschedule,
            "cancel": self._do_cancel,
            "escalate": self._escalate,
            "issue_refund": self._do_refund,
        }

    async def handle(self, inbound: InboundMessage) -> None:
        business = await self._d.businesses.for_channel(inbound.channel, inbound.to_address)
        if business is None:
            return  # not one of our numbers
        customer = await self._d.customers.upsert(
            business.id, inbound.channel, inbound.from_address
        )
        await self._d.conversations.append(
            customer, Message(MessageRole.CUSTOMER, inbound.text, inbound.received_at)
        )
        await self._d.events.publish(MessageReceived(business.id, customer.id, inbound.text))

        reply = await self._run(business, customer)

        await self._d.messaging.send(customer, OutboundMessage(reply))
        await self._d.conversations.append(
            customer, Message(MessageRole.ASSISTANT, reply, self._d.clock.now())
        )

    async def _run(self, business: Business, customer: Customer) -> str:
        messages = list(await self._d.conversations.history(customer))
        system = _system_prompt(business, await self._d.services.for_business(business.id))
        for _ in range(MAX_STEPS):
            completion = await self._d.llm.complete(
                system=system, messages=messages, tools=TOOL_SPECS
            )
            if not completion.tool_calls:
                return completion.text or ESCALATION_FALLBACK
            if completion.text:
                await self._observer.on_thought(completion.text)
            messages.append(
                Message(MessageRole.ASSISTANT, completion.text or "", self._d.clock.now())
            )
            for call in completion.tool_calls:
                result = await self._dispatch(business, customer, call)
                await self._observer.on_tool(call.name, call.args, result)
                messages.append(
                    Message(MessageRole.TOOL, result, self._d.clock.now(), tool_call_id=call.id)
                )
        return ESCALATION_FALLBACK

    async def _dispatch(self, business: Business, customer: Customer, call: ToolCall) -> str:
        handler = self._handlers.get(call.name)
        if handler is None:
            return f"Unknown tool: {call.name}"
        return await handler(business, customer, call.args)

    def _lookup_answer(self, business: Business, topic: str) -> str:
        needle = topic.casefold()
        for item in business.knowledge:
            if needle and (needle in item.question.casefold() or needle in item.answer.casefold()):
                return item.answer
        return "I don't have that information on hand — I can check with the team."

    async def _answer(self, business: Business, customer: Customer, args: dict[str, object]) -> str:
        return self._lookup_answer(business, _arg(args, "topic"))

    async def _find(self, business: Business, customer: Customer, args: dict[str, object]) -> str:
        service = await self._d.services.by_name(business.id, _arg(args, "service"))
        if service is None:
            return "I couldn't find that service."
        around = _parse_iso(args.get("around")) or self._d.clock.now()
        slots = await self._d.calendar.find_availability(service, around)
        if not slots:
            return "There are no free slots in that window."
        return "Free slots: " + _format_slots(slots)

    async def _do_book(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        service = await self._d.services.by_name(business.id, _arg(args, "service"))
        start = _parse_iso(args.get("start"))
        if service is None or start is None:
            return "I need a valid service and start time to book."
        slot = TimeSlot(start, start + timedelta(minutes=service.duration_minutes))
        try:
            appointment = await self._d.book(service, service.resource_ids[0], customer, slot)
        except DomainError as error:
            current = await self._d.calendar.find_availability(service, self._d.clock.now())
            return (
                f"Couldn't book that time ({error}) — it may have just passed or been taken. "
                f"The currently free slots are: {_format_slots(current)}. "
                "Offer these exact times; do not reuse any earlier list."
            )
        when = slot.starts_at.strftime(SLOT_FORMAT)
        return f"Booked {service.name} for {when}. Reference: {appointment.id}."

    async def _do_reschedule(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        start = _parse_iso(args.get("start"))
        if start is None:
            return "I need a valid new start time."
        appointment_id = AppointmentId(_arg(args, "appointment_id"))
        try:
            appointment = await self._d.appointments.get(appointment_id)
            service = await self._d.services.get(appointment.service_id)
            slot = TimeSlot(start, start + timedelta(minutes=service.duration_minutes))
            moved = await self._d.reschedule(appointment_id, slot)
        except DomainError as error:
            return f"I couldn't reschedule: {error}"
        return f"Moved to {moved.slot.starts_at.strftime(SLOT_FORMAT)}."

    async def _do_cancel(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        appointment_id = AppointmentId(_arg(args, "appointment_id"))
        try:
            await self._d.cancel(appointment_id)
        except DomainError as error:
            return f"I couldn't cancel: {error}"
        return "Your appointment is cancelled."

    async def _escalate(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        await self._d.events.publish(Escalated(business.id, customer.id, _arg(args, "reason")))
        return "I've passed this to a team member who will follow up shortly."

    async def _do_refund(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        # Sensitive: the model can't issue a refund on its own — it passes the gate.
        action = SensitiveAction(
            "issue_refund",
            args,
            f"Refund for {customer.channel_address} ({_arg(args, 'appointment_id')})",
        )
        decision = await self._d.gate.guard(action)
        if not decision.approved:
            await self._d.events.publish(ApprovalRequested(business.id, action.summary))
            return "That needs a team sign-off — I've flagged it and we'll confirm shortly."
        return "Your refund has been approved and issued."
