"""The assistant: a tool-use loop whose tools are the domain use cases.

The model decides *what* to attempt; the typed, tested core decides *whether and
how* it happens. It answers only from the knowledge base and the real calendar,
and escalates when unsure. See ADR-0007.
"""

import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
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
    Completion,
    ConversationRepository,
    CustomerRepository,
    Escalated,
    EventPublisher,
    InboundMessage,
    LlmProvider,
    MessageReceived,
    MessagingPort,
    OutboundMessage,
    ReplyClaim,
    ReplyClaimClassifier,
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
    ToolCallRef,
)

_logger = logging.getLogger("frontdesk.supervisor")

MAX_STEPS = 6
SLOT_FORMAT = "%a %d %b %H:%M"  # rendered in the business's local time zone
# Which claim each tool backs: if the reply makes a claim but its tool wasn't called this turn,
# the model is guessing/reusing stale data and the supervisor forces a redo with the real data.
_CLAIM_FOR_TOOL = {
    "find_availability": ReplyClaim.OFFERS_TIMES,
    "book": ReplyClaim.CONFIRMS_BOOKING,
    "reschedule": ReplyClaim.CONFIRMS_BOOKING,
    "cancel": ReplyClaim.CONFIRMS_BOOKING,
}
# Appended to the system prompt on the corrective retry. The backing tool is forced on that
# retry (tool_choice), so its fresh result enters the chat — these only steer how to use it.
_MAX_CORRECTIONS = 2  # at most this many corrective retries before sending the model's reply
_MAX_EMPTY_RETRIES = 2  # at most this many retries when the model returns nothing usable
_TIMES_NOTICE = (
    "\n\nSTOP: the appointment times in your previous draft are NOT real — you did not call "
    "find_availability this turn, you reused a list from earlier in the chat, and slots change "
    "constantly. Call find_availability now for the EXACT day the customer asked about, then "
    "show ONLY the slots it returns. Never show a time you did not get from find_availability."
)
_BOOKING_NOTICE = (
    "\n\nIMPORTANT: your previous draft told the customer a booking or change is done, but you "
    "did NOT call book, reschedule, or cancel this turn — so nothing happened. Either call the "
    "correct tool now (collect any required details first), or tell the customer it is not done."
)


@dataclass(frozen=True, slots=True)
class _Correction:
    """A supervisor fix: a system-prompt addendum, and the tool to force on the retry (if any)."""

    notice: str
    forced_tool: str | None


# A mutating tool succeeded only if its result is one of these confirmations (book / reschedule /
# cancel). Their failure results never contain these, so a faked "done" stays unverified.
_BOOKING_DONE_MARKERS = (
    "Booked ",
    "already booked for this customer",
    "Moved to ",
    "Your appointment is cancelled",
)


def _mutation_confirmed(result: str) -> bool:
    """True if a book/reschedule/cancel went through (vs returned an error to the model)."""
    return any(marker in result for marker in _BOOKING_DONE_MARKERS)


def _tool_call_refs(calls: Sequence[ToolCall]) -> tuple[ToolCallRef, ...]:
    """Carry the assistant's tool calls onto its history Message, so the next wire request keeps
    the assistant-turn → tool-result pairing that strict providers (Groq) require."""
    return tuple(ToolCallRef(call.id, call.name, json.dumps(call.args)) for call in calls)


# Tool results (fed back to the model) that steer it away from guessing appointment ids.
_NO_SUCH_APPOINTMENT = (
    "No appointment with that id exists. Use ONLY the appointment ids from the customer's "
    "appointments listed in the system prompt — never guess or recall an id from earlier."
)
_NOT_THEIRS = (
    "That appointment belongs to a different customer. Use the ids from this customer's own "
    "appointments listed in the system prompt."
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
        "reschedule",
        "Move an appointment to a new start time (ISO). Use an id from the customer's appointments "
        "listed in the system prompt.",
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
    classifier: ReplyClaimClassifier


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


def _normalize_field_key(key: str) -> str:
    """Match intake keys tolerantly: the model often copies the prompt's 'Name:' label verbatim,
    so 'Имя:' (or a quoted/spaced variant) must still match the field 'Имя'."""
    return key.strip().strip(":\"'`").strip().casefold()


def _collect_intake(
    service: Service, details: object
) -> tuple[tuple[IntakeAnswer, ...], list[str]]:
    """Map the model's answers to the service's fields; return (answers, missing field names)."""
    raw = details if isinstance(details, dict) else {}
    answers = {_normalize_field_key(str(key)): value for key, value in raw.items()}
    missing = [
        field.name
        for field in service.intake_fields
        if not str(answers.get(_normalize_field_key(field.name), "")).strip()
    ]
    collected = tuple(
        IntakeAnswer(field.name, str(answers[_normalize_field_key(field.name)]).strip())
        for field in service.intake_fields
        if field.name not in missing
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


def _system_prompt(
    business: Business, services: Sequence[Service], now: datetime, appointments: str
) -> str:
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
        "\n\nTo reschedule or cancel, use the customer's exact appointment id from the "
        "'Customer's appointments' section below — never guess an id or recall one from earlier in "
        "the chat. If they have no upcoming appointment, say so and offer to book a new one."
        f"\n\nThe time shown before each '(start=...)' is the FINAL local time in the business's "
        f"zone ({business.timezone}) — show exactly that time to the customer. Never ask the "
        "customer what time zone they are in, and never offer to convert times for them."
        f"{now_line}"
        f"{_intake_block(services)}"
        f"\n\n{appointments}"
        f"\n\nKnowledge base:\n{knowledge}"
    )


def _voice_system_prompt(
    business: Business, services: Sequence[Service], now: datetime, appointments: str
) -> str:
    """A terse, speech-tuned prompt for a phone call: a smaller prefill (lower latency) and rules
    written for spoken dialogue, not a messenger. Reuses the same data helpers as the text path."""
    menu = "\n".join(_menu_line(s) for s in services) or "- (none yet)"
    knowledge = "\n".join(f"Q: {item.question}\nA: {item.answer}" for item in business.knowledge)
    local_now = now.astimezone(ZoneInfo(business.timezone))
    about = f" {business.description}" if business.description else ""
    return (
        f"You are the phone receptionist for {business.name} — a warm, friendly, upbeat young "
        "woman. Be personable and human. In gendered languages always refer to yourself in the "
        "FEMININE (Russian: 'поняла', 'рада', 'готова' — never the masculine 'понял'/'готов')."
        f"{about}{_location_line(business)}\n\n"
        "This is a LIVE PHONE CALL — everything you say is spoken aloud. Reply in the caller's "
        "language in ONE or TWO short, natural sentences. Plain spoken words only: no Markdown, "
        "lists, ids, codes, URLs, emails, or ISO timestamps. "
        "CRITICAL: write every number, time, price and date as WORDS, never as digits or symbols — "
        "a digit read aloud sounds robotic (write 'half past one in the afternoon', not '13:30'; "
        "'an hour and a half', not '1.5 h'; 'the first of July', not '01.07'). "
        "Before a tool runs, say one short line about what you're doing (e.g. 'one moment, let me "
        "check').\n\n"
        "Use the tools for real availability and booking — never invent times, prices, "
        "or services. These are the ONLY services; if asked for anything else, say you "
        f"don't offer it:\n{menu}\n\n"
        "Collect booking details ONE at a time: ask for the next single item and wait. Call "
        "find_availability right before offering times, offer at most three, and never reuse an "
        "earlier list. To change or cancel, use the customer's existing appointment listed below — "
        "reschedule or cancel that one; do NOT offer new slots or re-ask details you can already "
        "see. If the caller already has the appointment they ask about, simply confirm it."
        f"{_intake_block(services)}"
        f"\n\nThe current date and time is {local_now.strftime('%A, %d %B %Y, %H:%M')} "
        f"({business.timezone}, {_utc_offset(local_now)}). Turn 'today'/'tomorrow'/a weekday into "
        "exact ISO datetimes for the tools."
        f"\n\n{appointments}"
        f"\n\nKnowledge base:\n{knowledge}"
    )


# A sentence ends at .!?… (with any closing quote/bracket) followed by whitespace. Used to flush
# whole sentences from the streamed reply, so text-to-speech speaks natural units, not fragments.
_SENTENCE_BOUNDARY = re.compile(r"[.!?…]+[\"»”’)\]]*\s+")


def _drain_sentences(buffer: str) -> tuple[list[str], str]:
    """Split complete sentences off the front of ``buffer``, keeping the trailing fragment so a
    sentence is spoken only once it is whole. Returns (complete sentences, leftover fragment)."""
    sentences: list[str] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(buffer):
        sentences.append(buffer[start : match.end()].strip())
        start = match.end()
    return sentences, buffer[start:]


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
        messages = self._initial_messages(await self._d.conversations.history(customer), business)
        system = _system_prompt(
            business,
            await self._d.services.for_business(business.id),
            self._d.clock.now(),
            await self._appointments_block(business, customer),
        )
        verified: set[ReplyClaim] = set()  # claims backed by a tool call this turn
        corrections = 0  # how many corrective retries the supervisor has spent
        empty_retries = 0  # how many empty (no text, no tool) completions we've retried
        forced_tool: str | None = None  # the tool the next retry must call (tool_choice)
        for _ in range(MAX_STEPS):
            completion = await self._d.llm.complete(
                system=system, messages=messages, tools=TOOL_SPECS, tool_choice=forced_tool
            )
            forced_tool = None  # force at most the single next call
            if not completion.tool_calls:
                if not completion.text:
                    # The model emitted nothing usable (often a reasoning model that ran out of
                    # room). Retry a couple of times before falling back to a human hand-off,
                    # rather than send the customer a dead end.
                    if empty_retries < _MAX_EMPTY_RETRIES:
                        empty_retries += 1
                        _logger.info("empty completion — retrying (business=%s)", business.id)
                        continue
                    return _escalation(business)
                reply = completion.text
                correction = (
                    None
                    if corrections >= _MAX_CORRECTIONS
                    else await self._claim_correction(reply, verified)
                )
                if correction is None:
                    return reply
                _logger.info(
                    "supervisor corrected an unverified-claim reply (business=%s)", business.id
                )
                system += correction.notice
                forced_tool = correction.forced_tool
                corrections += 1
                continue
            if completion.text:
                await self._observer.on_thought(completion.text)
            messages.append(
                Message(
                    MessageRole.ASSISTANT,
                    completion.text or "",
                    self._d.clock.now(),
                    tool_calls=_tool_call_refs(completion.tool_calls),
                )
            )
            for call in completion.tool_calls:
                result = await self._dispatch(business, customer, call)
                claim = _CLAIM_FOR_TOOL.get(call.name)
                # A booking claim counts only when the mutation actually SUCCEEDED — a called-but-
                # failed book/reschedule/cancel must not let the model claim it is done.
                if claim is not None and (
                    claim is not ReplyClaim.CONFIRMS_BOOKING or _mutation_confirmed(result)
                ):
                    verified.add(claim)
                await self._observer.on_tool(call.name, call.args, result)
                messages.append(
                    Message(MessageRole.TOOL, result, self._d.clock.now(), tool_call_id=call.id)
                )
        return _escalation(business)

    async def stream(self, business: Business, customer: Customer) -> AsyncIterator[str]:
        """A voice turn: run the tool loop, speaking each step as it happens.

        Yields each spoken line as the model produces it — a short narration before a tool runs
        ('Let me check Friday…'), then the final answer — so the caller's text-to-speech has no
        dead air. The reply-claim supervisor is intentionally OFF this hot path for latency
        (VOICE_RECEPTIONIST.md §6); the no-false-booking floor still holds via the appointments
        injected into the prompt and the deterministic booking receipt. Re-validate the guardrails
        against the voice model in Phase 0. Persistence is the caller's job, as in ``_run``.
        """
        messages = self._initial_messages(await self._d.conversations.history(customer), business)
        system = _voice_system_prompt(
            business,
            await self._d.services.for_business(business.id),
            self._d.clock.now(),
            await self._appointments_block(business, customer),
        )
        spoke = False  # whether we have yielded any text this turn
        empty_retries = 0
        for _ in range(MAX_STEPS):
            completion = Completion(text=None)
            buffer = ""
            async for chunk in self._d.llm.complete_stream(
                system=system, messages=messages, tools=TOOL_SPECS
            ):
                if chunk.text_delta:
                    buffer += chunk.text_delta
                    sentences, buffer = _drain_sentences(buffer)
                    for sentence in sentences:  # speak each sentence as soon as it is whole
                        spoke = True
                        yield sentence
                if chunk.completion is not None:
                    completion = chunk.completion
            if tail := buffer.strip():  # flush this turn's trailing fragment before acting
                spoke = True
                yield tail
            if not completion.tool_calls:
                if not completion.text and empty_retries < _MAX_EMPTY_RETRIES:
                    empty_retries += 1
                    continue
                if not spoke:
                    yield _escalation(business)
                return
            await self._run_tools(business, customer, completion, messages)
        if not spoke:  # the loop ran out of steps without ever speaking — hand off
            yield _escalation(business)

    async def _run_tools(
        self,
        business: Business,
        customer: Customer,
        completion: Completion,
        messages: list[Message],
    ) -> None:
        """Record the assistant's tool-call turn, then run each tool and append its result."""
        messages.append(
            Message(
                MessageRole.ASSISTANT,
                completion.text or "",
                self._d.clock.now(),
                tool_calls=_tool_call_refs(completion.tool_calls),
            )
        )
        for call in completion.tool_calls:
            result = await self._dispatch(business, customer, call)
            await self._observer.on_tool(call.name, call.args, result)
            messages.append(
                Message(MessageRole.TOOL, result, self._d.clock.now(), tool_call_id=call.id)
            )

    def _initial_messages(self, history: Sequence[Message], business: Business) -> list[Message]:
        # Mark the owner's hand-written turns so the model treats them as the human owner,
        # not as its own past replies (owner turns map to the assistant role for the LLM).
        tag = _owner_tag(business)
        return [
            replace(message, text=tag + message.text)
            if message.role is MessageRole.OWNER
            else message
            for message in history
        ]

    async def _claim_correction(self, reply: str, verified: set[ReplyClaim]) -> _Correction | None:
        """How to fix a reply whose claims aren't all backed by tools, or None when they are.

        The retry forces the tool that backs the strongest unverified claim, so reality enters the
        chat: a faked booking forces book (it then really books, or fails and the model must
        recant); offered times force a fresh find_availability. (The customer's appointments are
        always in the prompt, so a recited list needs no tool and is not supervised here.)
        """
        unverified = await self._d.classifier.classify(reply) - verified
        if not unverified:
            return None
        # A faked booking is the most harmful claim, so it takes priority on the one forced retry.
        if ReplyClaim.CONFIRMS_BOOKING in unverified:
            return _Correction(_BOOKING_NOTICE, "book")
        return _Correction(_TIMES_NOTICE, "find_availability")  # the only other claim is times

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

    async def _appointments_block(self, business: Business, customer: Customer) -> str:
        """The customer's real appointments, injected into the prompt so the model never guesses or
        recalls them: every upcoming one (with its id) plus the last 10 that have already passed."""
        tz = ZoneInfo(business.timezone)
        now = self._d.clock.now()
        mine = [
            appointment
            for appointment in await self._d.appointments.for_business(business.id)
            if appointment.customer_id == customer.id
            and appointment.status != AppointmentStatus.CANCELLED
        ]
        upcoming = sorted(
            (a for a in mine if a.slot.starts_at >= now), key=lambda a: a.slot.starts_at
        )
        past = sorted(
            (a for a in mine if a.slot.starts_at < now),
            key=lambda a: a.slot.starts_at,
            reverse=True,
        )[:10]
        rendered: dict[str, list[str]] = {"upcoming": [], "past": []}
        for bucket, items in (("upcoming", upcoming), ("past", past)):
            for appointment in items:
                service = await self._d.services.get(appointment.service_id)
                rendered[bucket].append(
                    f"- id={appointment.id} | {service.name} | "
                    f"{_when(appointment.slot.starts_at, tz)} | {appointment.status.value}"
                )
        return (
            "Customer's appointments (ALWAYS the live truth — use ONLY this when stating, listing, "
            "rescheduling, or cancelling; never add, drop, or recall any from earlier in the "
            "chat):\nUpcoming:\n" + ("\n".join(rendered["upcoming"]) or "(none)") + "\n"
            "Recent past (already happened):\n" + ("\n".join(rendered["past"]) or "(none)")
        )

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
        when = _when(slot.starts_at, tz)
        try:
            appointment = await self._d.book(
                service, service.resource_ids[0], customer, slot, intake
            )
        except DomainError as error:
            # The model sometimes calls book twice for the same slot in one turn; the second call
            # clashes with the first. If this customer already holds this exact slot, it's that
            # duplicate — report success, never tell them their own booking's slot is taken.
            if await self._already_booked(business, customer, service, slot):
                return (
                    f"{service.name} for {when} is already booked for this customer and the "
                    "confirmation was sent — just acknowledge warmly. Do NOT tell them the slot "
                    "is unavailable and do NOT offer other times."
                )
            current = await self._d.calendar.find_availability(service, self._d.clock.now())
            return (
                f"Couldn't book that time ({error}) — it may have just passed or been taken. "
                f"The currently free slots are: {_format_slots(current, tz)}. "
                "Offer these exact times; do not reuse any earlier list."
            )
        await self._d.messaging.send(
            customer, OutboundMessage(_booking_receipt(business, service, slot.starts_at, intake))
        )
        return (
            f"Booked {service.name} for {when} (ref {appointment.id}). A confirmation with the "
            "details was already sent to the customer — acknowledge warmly and briefly."
        )

    async def _already_booked(
        self, business: Business, customer: Customer, service: Service, slot: TimeSlot
    ) -> bool:
        """True if this customer already holds this exact (service, start) — a duplicate book."""
        return any(
            appointment.customer_id == customer.id
            and appointment.service_id == service.id
            and appointment.slot.starts_at == slot.starts_at
            and appointment.status != AppointmentStatus.CANCELLED
            for appointment in await self._d.appointments.for_business(business.id)
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
        appointment_id = AppointmentId(_arg(args, "appointment_id"))
        try:
            appointment = await self._d.appointments.get(appointment_id)
        except DomainError:
            return _NO_SUCH_APPOINTMENT
        # Never let a refund request reference another customer's appointment, even if the model
        # is prompt-injected into passing a foreign id. The human gate still approves the rest.
        if appointment.customer_id != customer.id:
            return _NOT_THEIRS
        # Sensitive: the model can't issue a refund on its own — it passes the gate.
        action = SensitiveAction(
            str(business.id),
            "issue_refund",
            args,
            f"Refund for {customer.channel_address} ({appointment_id})",
        )
        decision = await self._d.gate.guard(action)
        if not decision.approved:
            await self._d.events.publish(ApprovalRequested(business.id, action.summary))
            return "That needs a team sign-off — I've flagged it and we'll confirm shortly."
        return "Your refund has been approved and issued."
