"""The assistant: a tool-use loop whose tools are the domain use cases.

The model decides *what* to attempt; the typed, tested core decides *whether and
how* it happens. It answers only from the knowledge base and the real calendar,
and escalates when unsure. See ADR-0007.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    RescheduleAppointment,
)
from frontdesk.application.datetime_format import format_when
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
from frontdesk.domain.enums import AppointmentStatus, MessageRole
from frontdesk.domain.errors import DomainError
from frontdesk.domain.ids import AppointmentId
from frontdesk.domain.models import (
    Business,
    Customer,
    IntakeAnswer,
    Message,
    Service,
    TimeSlot,
)

MAX_STEPS = 6
SLOT_FORMAT = "%a %d %b %H:%M"  # rendered in the business's local time zone
# Tool results (fed back to the model) that steer it away from guessing appointment ids.
_NO_SUCH_APPOINTMENT = (
    "No appointment with that id exists. Call find_my_appointments to get the customer's real "
    "appointment ids — never guess or recall an id from earlier in the chat."
)
_NOT_THEIRS = (
    "That appointment belongs to a different customer. Use find_my_appointments to find this "
    "customer's own appointments."
)

# Sent verbatim to the customer (not via the model), so it carries the business's language.
ESCALATION_FALLBACK = {
    "en": "Let me get a colleague to help you with that — they'll be in touch shortly.",
    "es": "Déjame pasar esto a un compañero — se pondrá en contacto contigo en breve.",
    "ru": "Передам это коллеге — он скоро свяжется с вами.",
    "zh": "我帮您转交给同事，他们会尽快与您联系。",
}


def _escalation(business: Business) -> str:
    return ESCALATION_FALLBACK.get(business.locale, ESCALATION_FALLBACK["en"])


# Prepended to the assistant's conversational replies so the customer knows the AI is
# answering (vs the business owner, who replies under their own name — see owner takeover).
_AI_PREFIX = {
    "en": "[AI assistant]: ",
    "es": "[Asistente IA]: ",
    "ru": "[ИИ-ассистент]: ",
    "zh": "[AI 助手]：",
}


def ai_prefix_for(locale: str) -> str:
    """The localized '[AI assistant]: ' tag shown on every message the AI sends."""
    return _AI_PREFIX.get(locale, _AI_PREFIX["en"])


def _ai_prefix(business: Business) -> str:
    return ai_prefix_for(business.locale)


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
        "Book an appointment for a service at a slot start time (ISO). Pass 'details' with "
        "the service's required intake answers (a map of field name to the customer's answer).",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "start": {"type": "string"},
                "details": {"type": "object"},
            },
            "required": ["service", "start"],
        },
    ),
    ToolSpec(
        "find_my_appointments",
        "List THIS customer's upcoming appointments with their exact ids — call this before "
        "any reschedule or cancel to get the real id (never guess one).",
        {"type": "object", "properties": {}},
    ),
    ToolSpec(
        "reschedule",
        "Move an appointment to a new start time (ISO). Use an id from find_my_appointments.",
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


def _when(moment: datetime, tz: ZoneInfo) -> str:
    """A start time rendered in the business's local time zone."""
    return moment.astimezone(tz).strftime(SLOT_FORMAT)


def _utc_offset(moment: datetime) -> str:
    """The offset of an aware datetime as 'UTC-3' / 'UTC+5:30'."""
    minutes = int((moment.utcoffset() or timedelta()).total_seconds() // 60)
    hours, mins = divmod(abs(minutes), 60)
    return f"UTC{'+' if minutes >= 0 else '-'}{hours}" + (f":{mins:02d}" if mins else "")


# Sent verbatim to the customer when a booking is created — localized by business.locale.
_RECEIPT = {
    "en": ("✅ Booking confirmed", "Your details:"),
    "es": ("✅ Reserva confirmada", "Tus datos:"),
    "ru": ("✅ Запись подтверждена", "Ваши данные:"),
    "zh": ("✅ 预约已确认", "您的信息："),
}


def _booking_receipt(
    business: Business, service: Service, moment: datetime, intake: Sequence[IntakeAnswer]
) -> str:
    """A deterministic confirmation: what was booked, when, and the captured answers."""
    booked, details = _RECEIPT.get(business.locale, _RECEIPT["en"])
    lines = [booked, f"**{service.name}**", f"📅 {format_when(moment, business)}"]
    if intake:
        lines += ["", details, *(f"• {answer.name}: {answer.value}" for answer in intake)]
    return "\n".join(lines)


def _collect_intake(
    service: Service, details: object
) -> tuple[tuple[IntakeAnswer, ...], list[str]]:
    """Map the model's answers to the service's fields; return (answers, missing field names)."""
    answers = details if isinstance(details, dict) else {}
    missing = [f.name for f in service.intake_fields if not str(answers.get(f.name, "")).strip()]
    collected = tuple(
        IntakeAnswer(f.name, str(answers[f.name]).strip())
        for f in service.intake_fields
        if f.name not in missing
    )
    return collected, missing


def _format_slots(slots: Sequence[TimeSlot], tz: ZoneInfo) -> str:
    if not slots:
        return "no free times right now"
    # Show local time to the customer; keep the UTC ISO so the model books the exact slot.
    return "; ".join(f"{_when(s.starts_at, tz)} (start={s.starts_at.isoformat()})" for s in slots)


def _menu_line(service: Service) -> str:
    line = f"- {service.name} ({service.duration_minutes} min)"
    return f"{line} — {service.description}" if service.description else line


def _location_line(business: Business) -> str:
    if business.online:
        return "\n\nThis business is online — appointments are remote; there is no address."
    if business.address:
        return f"\n\nLocation: {business.address}"
    return ""


def _owner_tag(business: Business) -> str:
    """The marker prepended to owner turns in the history the model reads."""
    name = business.owner_name.strip()
    return f"[owner {name}] " if name else "[owner] "


def _owner_line(business: Business) -> str:
    """Tell the model who the human owner is, and how to read their turns in the history."""
    name = business.owner_name.strip()
    who = f", {name}," if name else ""
    return (
        f"\n\nThe business has a human owner{who} who can step into a chat to reply in person. "
        f"A message in the history that starts with '{_owner_tag(business).strip()}' was written "
        "by the owner, NOT by you — treat it as the owner speaking to the customer, and continue "
        "naturally from where they left off (do not repeat or contradict them)."
    )


def _intake_block(services: Sequence[Service]) -> str:
    blocks = []
    for service in services:
        if not service.intake_fields:
            continue
        fields = "\n".join(
            f"  - {f.name}: {f.description}" + (f" (e.g. ask: {f.ask})" if f.ask else "")
            for f in service.intake_fields
        )
        blocks.append(
            f"For '{service.name}', collect ALL of these from the customer BEFORE booking and "
            f"pass them in the book tool's 'details' (keyed by the exact field name):\n{fields}"
        )
    return "\n\nIntake required before booking:\n" + "\n\n".join(blocks) if blocks else ""


def _system_prompt(business: Business, services: Sequence[Service], now: datetime) -> str:
    menu = "\n".join(_menu_line(s) for s in services) or "- (none yet)"
    knowledge = "\n".join(f"Q: {item.question}\nA: {item.answer}" for item in business.knowledge)
    about = f"\n\nAbout {business.name}:\n{business.description}" if business.description else ""
    local_now = now.astimezone(ZoneInfo(business.timezone))
    now_line = (
        f"\n\nThe current date and time is {local_now.strftime('%A, %d %B %Y, %H:%M')} in the "
        f"business's time zone ({business.timezone}, {_utc_offset(local_now)}). Use this exact "
        "date, weekday, time and UTC offset to turn relative dates like 'today', 'tomorrow', or a "
        "weekday name into exact ISO datetimes for find_availability and book."
    )
    return (
        f"You are the front desk for {business.name}. Be brief and warm, and reply in the "
        "customer's language. Use the tools to check real availability and to book — never "
        "invent times, prices, services, or facts. Escalate when you cannot help.\n\n"
        "You may use light Markdown — **bold**, *italic*, `code`, bullet lists with '- ', and "
        "[links](https://...). It renders natively in the customer's messenger. Keep it simple: "
        "prefer short bullet lists over tables, and avoid headings."
        f"{about}{_location_line(business)}{_owner_line(business)}\n\n"
        "These are the ONLY services we offer. Never offer, suggest, or search for anything "
        f"not on this list — if a customer asks for something else, say we don't offer it:\n{menu}"
        "\n\nFree times change after EVERY booking, reschedule, or cancellation — and as time "
        "passes. You MUST call find_availability again right before you show any times, and NEVER "
        "reuse or recall a list of times from earlier in the chat: an earlier list is stale the "
        "moment anything is booked. If a booking fails, the tool returns the current free slots — "
        "offer exactly those."
        "\n\nTo reschedule or cancel, you MUST first call find_my_appointments to get the "
        "customer's exact appointment id — never guess an id or recall one from earlier in the "
        "chat. If they have no upcoming appointment, say so and offer to book a new one."
        f"\n\nThe time shown before each '(start=...)' is the FINAL local time in the business's "
        f"zone ({business.timezone}) — show exactly that time to the customer. Never ask the "
        "customer what time zone they are in, and never offer to convert times for them."
        f"{now_line}"
        f"{_intake_block(services)}"
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
            "find_my_appointments": self._find_appointments,
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
            business.id, inbound.channel, inbound.from_address, inbound.sender_name
        )
        await self._d.conversations.append(
            customer, Message(MessageRole.CUSTOMER, inbound.text, inbound.received_at)
        )
        await self._d.events.publish(MessageReceived(business.id, customer.id, inbound.text))

        if customer.handled_by_owner:
            return  # the owner has taken over; the assistant stays silent

        reply = await self._run(business, customer)

        # The customer sees who is speaking; the history keeps the clean text.
        await self._d.messaging.send(customer, OutboundMessage(_ai_prefix(business) + reply))
        await self._d.conversations.append(
            customer, Message(MessageRole.ASSISTANT, reply, self._d.clock.now())
        )

    async def _run(self, business: Business, customer: Customer) -> str:
        history = await self._d.conversations.history(customer)
        # Mark the owner's hand-written turns so the model treats them as the human owner,
        # not as its own past replies (owner turns map to the assistant role for the LLM).
        tag = _owner_tag(business)
        messages = [
            replace(message, text=tag + message.text)
            if message.role is MessageRole.OWNER
            else message
            for message in history
        ]
        system = _system_prompt(
            business, await self._d.services.for_business(business.id), self._d.clock.now()
        )
        for _ in range(MAX_STEPS):
            completion = await self._d.llm.complete(
                system=system, messages=messages, tools=TOOL_SPECS
            )
            if not completion.tool_calls:
                return completion.text or _escalation(business)
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
        return _escalation(business)

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
        return "Free slots: " + _format_slots(slots, ZoneInfo(business.timezone))

    async def _find_appointments(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        tz = ZoneInfo(business.timezone)
        now = self._d.clock.now()
        mine = sorted(
            (
                appointment
                for appointment in await self._d.appointments.for_business(business.id)
                if appointment.customer_id == customer.id
                and appointment.status != AppointmentStatus.CANCELLED
                and appointment.slot.starts_at >= now
            ),
            key=lambda a: a.slot.starts_at,
        )
        if not mine:
            return "The customer has no upcoming appointments."
        lines = []
        for appointment in mine:
            service = await self._d.services.get(appointment.service_id)
            lines.append(
                f"- id={appointment.id} | {service.name} | {_when(appointment.slot.starts_at, tz)}"
            )
        return "The customer's upcoming appointments:\n" + "\n".join(lines)

    async def _do_book(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        service = await self._d.services.by_name(business.id, _arg(args, "service"))
        start = _parse_iso(args.get("start"))
        if service is None or start is None:
            return "I need a valid service and start time to book."
        intake, missing = _collect_intake(service, args.get("details"))
        if missing:
            return (
                "Before booking, you must collect ALL of these from the customer, then call book "
                f"again with them in 'details': {', '.join(missing)}."
            )
        tz = ZoneInfo(business.timezone)
        slot = TimeSlot(start, start + timedelta(minutes=service.duration_minutes))
        try:
            appointment = await self._d.book(
                service, service.resource_ids[0], customer, slot, intake
            )
        except DomainError as error:
            current = await self._d.calendar.find_availability(service, self._d.clock.now())
            return (
                f"Couldn't book that time ({error}) — it may have just passed or been taken. "
                f"The currently free slots are: {_format_slots(current, tz)}. "
                "Offer these exact times; do not reuse any earlier list."
            )
        when = _when(slot.starts_at, tz)
        await self._d.messaging.send(
            customer, OutboundMessage(_booking_receipt(business, service, slot.starts_at, intake))
        )
        return (
            f"Booked {service.name} for {when} (ref {appointment.id}). A confirmation with the "
            "details was already sent to the customer — acknowledge warmly and briefly."
        )

    async def _do_reschedule(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        start = _parse_iso(args.get("start"))
        if start is None:
            return "I need a valid new start time."
        appointment_id = AppointmentId(_arg(args, "appointment_id"))
        try:
            appointment = await self._d.appointments.get(appointment_id)
            if appointment.customer_id != customer.id:
                return _NOT_THEIRS
            service = await self._d.services.get(appointment.service_id)
            slot = TimeSlot(start, start + timedelta(minutes=service.duration_minutes))
            moved = await self._d.reschedule(appointment_id, slot)
        except DomainError:
            return _NO_SUCH_APPOINTMENT
        return f"Moved to {_when(moved.slot.starts_at, ZoneInfo(business.timezone))}."

    async def _do_cancel(
        self, business: Business, customer: Customer, args: dict[str, object]
    ) -> str:
        appointment_id = AppointmentId(_arg(args, "appointment_id"))
        try:
            appointment = await self._d.appointments.get(appointment_id)
            if appointment.customer_id != customer.id:
                return _NOT_THEIRS
            await self._d.cancel(appointment_id)
        except DomainError:
            return _NO_SUCH_APPOINTMENT
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
            str(business.id),
            "issue_refund",
            args,
            f"Refund for {customer.channel_address} ({_arg(args, 'appointment_id')})",
        )
        decision = await self._d.gate.guard(action)
        if not decision.approved:
            await self._d.events.publish(ApprovalRequested(business.id, action.summary))
            return "That needs a team sign-off — I've flagged it and we'll confirm shortly."
        return "Your refund has been approved and issued."
