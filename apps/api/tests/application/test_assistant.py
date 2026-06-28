"""The assistant loop: the answer, booking, and escalation flows end-to-end."""

from datetime import UTC, datetime

from frontdesk.application.assistant import ESCALATION_FALLBACK, MAX_STEPS, _system_prompt
from frontdesk.application.ports import (
    AppointmentBooked,
    ApprovalRequested,
    Completion,
    Escalated,
    InboundMessage,
    MessageReceived,
    ReplyClaim,
    ToolCall,
)
from frontdesk.domain.enums import AppointmentStatus, Channel, MessageRole
from frontdesk.domain.ids import AppointmentId, BusinessId, CustomerId
from frontdesk.domain.models import Customer, IntakeAnswer, IntakeField, Message, TimeSlot
from frontdesk.infrastructure.memory import (
    InMemoryReplyClaimClassifier,
    ScriptedLlmProvider,
)
from tests.application.world import NOW, build_world, inbound, make_customer

_SLOT = TimeSlot(datetime(2026, 6, 26, 15, tzinfo=UTC), datetime(2026, 6, 26, 16, tzinfo=UTC))


def _tool(call_id: str, name: str, args: dict[str, object]) -> Completion:
    return Completion(None, (ToolCall(call_id, name, args),))


async def test_answer_flow_relays_knowledge() -> None:
    world = build_world(
        [
            _tool("1", "answer_question", {"topic": "hours"}),
            Completion("We're open 9 to 17, Monday to Friday."),
        ]
    )

    await world.assistant.handle(inbound("what are your opening hours?"))

    assert world.messaging.sent[-1][1].text.endswith("We're open 9 to 17, Monday to Friday.")
    assert any(isinstance(event, MessageReceived) for event in world.events.events)


async def test_booking_flow_books_and_schedules_reminders() -> None:
    start = "2026-06-26T15:00:00+00:00"  # 15:00 today: the 2h reminder (13:00) is in the future
    world = build_world(
        [
            _tool("1", "find_availability", {"service": "Haircut"}),
            _tool("2", "book", {"service": "Haircut", "start": start}),
            Completion("You're booked!"),
        ]
    )

    await world.assistant.handle(inbound("can I get a haircut at 3pm?"))

    assert world.messaging.sent[-1][1].text.endswith("You're booked!")
    appointments = list(world.appointments.appointments.values())
    assert len(appointments) == 1
    assert appointments[0].status == AppointmentStatus.CONFIRMED  # auto-confirmed by default
    assert any(isinstance(event, AppointmentBooked) for event in world.events.events)
    assert len(world.reminders.reminders) == 1  # only the future 2h reminder


async def test_escalation_flow_hands_off() -> None:
    world = build_world(
        [
            _tool("1", "escalate", {"reason": "upset customer"}),
            Completion("A team member will follow up shortly."),
        ]
    )

    await world.assistant.handle(inbound("this is unacceptable!"))

    assert any(isinstance(event, Escalated) for event in world.events.events)
    assert world.messaging.sent[-1][1].text.endswith("A team member will follow up shortly.")


async def test_failed_booking_returns_current_availability() -> None:
    world = build_world([])
    args: dict[str, object] = {"service": "Haircut", "start": "2026-06-26T12:00:00+00:00"}

    first = await world.assistant._do_book(world.business, make_customer(), args)
    # A DIFFERENT customer hits the taken slot — a genuine clash, not a duplicate.
    other = Customer(CustomerId("cus-2"), BusinessId("biz"), Channel.WHATSAPP, "+other")
    retry = await world.assistant._do_book(world.business, other, args)

    assert "Booked" in first
    assert "currently free" in retry.lower()  # the model gets ground truth, not a stale list


async def test_duplicate_book_by_same_customer_is_idempotent() -> None:
    # The model sometimes calls book twice for the same slot in one turn. The second call must
    # NOT tell the customer their own just-booked slot is taken — it reports the booking instead.
    world = build_world([])
    customer = make_customer()
    args: dict[str, object] = {"service": "Haircut", "start": "2026-06-26T12:00:00+00:00"}

    first = await world.assistant._do_book(world.business, customer, args)
    again = await world.assistant._do_book(world.business, customer, args)  # same customer + slot

    assert "Booked" in first
    assert "already booked" in again.lower()
    assert "currently free" not in again.lower()  # not the clash path
    assert len(world.appointments.appointments) == 1  # no duplicate appointment created


def test_system_prompt_lists_only_real_services() -> None:
    world = build_world([])

    prompt = _system_prompt(world.business, [world.service], NOW)

    assert "Haircut" in prompt
    assert "ONLY services" in prompt
    assert "never invent" in prompt.lower()


def test_answer_is_grounded() -> None:
    world = build_world([])

    assert "9 to 17" in world.assistant._lookup_answer(world.business, "hours")
    assert "don't have that information" in world.assistant._lookup_answer(
        world.business, "parking"
    )


async def test_unknown_business_number_is_ignored() -> None:
    world = build_world([Completion("hi")])

    await world.assistant.handle(
        InboundMessage(Channel.WHATSAPP, "+CUST", "+WRONG", "hi", NOW, "x")
    )

    assert world.messaging.sent == []


async def test_max_steps_falls_back_to_escalation() -> None:
    script = [_tool(str(i), "answer_question", {"topic": "x"}) for i in range(MAX_STEPS + 1)]
    world = build_world(script)

    await world.assistant.handle(inbound("loop forever"))

    assert world.messaging.sent[-1][1].text.endswith(
        ESCALATION_FALLBACK["en"]
    )  # world business is en


async def test_book_reschedule_cancel_via_loop() -> None:
    world = build_world(
        [
            _tool("1", "book", {"service": "Haircut", "start": "2026-06-26T15:00:00+00:00"}),
            _tool(
                "2", "reschedule", {"appointment_id": "ap-1", "start": "2026-06-26T16:00:00+00:00"}
            ),
            _tool("3", "cancel", {"appointment_id": "ap-1"}),
            Completion("All sorted!"),
        ]
    )

    await world.assistant.handle(inbound("book, move, then cancel"))

    appointment = world.appointments.appointments[AppointmentId("ap-1")]
    assert appointment.slot.starts_at.isoformat() == "2026-06-26T16:00:00+00:00"
    assert appointment.status == AppointmentStatus.CANCELLED
    assert world.messaging.sent[-1][1].text.endswith("All sorted!")


async def test_find_availability_reports_unknown_service() -> None:
    world = build_world(
        [
            _tool("1", "find_availability", {"service": "Massage"}),
            Completion("Sorry, we don't offer that yet."),
        ]
    )

    await world.assistant.handle(inbound("do you do massages?"))

    assert world.messaging.sent[-1][1].text.endswith("Sorry, we don't offer that yet.")


async def test_sensitive_refund_is_gated_when_not_approved() -> None:
    world = build_world(
        [
            _tool("1", "issue_refund", {"appointment_id": "ap-1", "amount": 49.99}),
            Completion("I've flagged your refund for approval."),
        ],
        gate_approves=False,
    )

    await world.assistant.handle(inbound("I want a refund please"))

    assert any(isinstance(event, ApprovalRequested) for event in world.events.events)


async def test_sensitive_refund_runs_when_approved() -> None:
    world = build_world(
        [
            _tool("1", "issue_refund", {"appointment_id": "ap-1", "amount": 49.99}),
            Completion("Your refund is on its way."),
        ],
        gate_approves=True,
    )

    await world.assistant.handle(inbound("I want a refund please"))

    assert not any(isinstance(event, ApprovalRequested) for event in world.events.events)


async def test_booking_collects_intake_then_sends_a_receipt() -> None:
    start = "2026-06-26T15:00:00+00:00"
    world = build_world(
        [
            # First the model tries to book without the required field → blocked.
            _tool("1", "book", {"service": "Haircut", "start": start}),
            # Then it books with the collected answer in 'details'.
            _tool(
                "2",
                "book",
                {"service": "Haircut", "start": start, "details": {"Birth date": "1990-01-01"}},
            ),
            Completion("All set!"),
        ],
        intake_fields=(IntakeField("Birth date", "the customer's date of birth"),),
    )

    await world.assistant.handle(inbound("book me a haircut"))

    # The deterministic receipt carried the captured answer.
    receipts = [message.text for _, message in world.messaging.sent]
    assert any("Birth date: 1990-01-01" in text for text in receipts)
    # The appointment persisted the intake answer.
    appointment = next(iter(world.appointments.appointments.values()))
    assert appointment.intake == (IntakeAnswer("Birth date", "1990-01-01"),)


async def test_book_accepts_intake_keys_with_a_trailing_colon() -> None:
    # The model copies the prompt's "Birth date:" label as the key. Matching must tolerate it,
    # or the first book fails on "missing intake" and the model fabricates a confirmation.
    world = build_world([], intake_fields=(IntakeField("Birth date", "date of birth"),))
    args: dict[str, object] = {
        "service": "Haircut",
        "start": "2026-06-26T15:00:00+00:00",
        "details": {"Birth date:": "1990-01-01"},  # note the spurious trailing colon
    }

    result = await world.assistant._do_book(world.business, make_customer(), args)

    assert "Booked" in result  # the colon-suffixed key still matched the field
    appointment = next(iter(world.appointments.appointments.values()))
    assert appointment.intake == (IntakeAnswer("Birth date", "1990-01-01"),)


async def test_find_my_appointments_lists_the_customers_upcoming_with_real_ids() -> None:
    world = build_world([])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+CUST")
    appointment = await world.book(world.service, world.service.resource_ids[0], customer, _SLOT)

    result = await world.assistant._find_appointments(world.business, customer, {})

    assert str(appointment.id) in result  # the real id, so the model never has to guess
    assert "Haircut" in result


async def test_reschedule_unknown_id_steers_to_lookup() -> None:
    world = build_world([])

    result = await world.assistant._do_reschedule(
        world.business,
        make_customer(),
        {"appointment_id": "made-up", "start": "2026-06-26T15:00:00+00:00"},
    )

    assert "find_my_appointments" in result  # don't guess — look it up


async def test_cancel_anothers_appointment_is_refused() -> None:
    world = build_world([])
    owner = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+OWNER")
    intruder = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+INTRUDER")
    appointment = await world.book(world.service, world.service.resource_ids[0], owner, _SLOT)

    result = await world.assistant._do_cancel(
        world.business, intruder, {"appointment_id": str(appointment.id)}
    )

    assert "different customer" in result
    assert world.appointments.appointments[appointment.id].status != AppointmentStatus.CANCELLED


async def test_assistant_reply_carries_the_ai_prefix_but_history_stays_clean() -> None:
    world = build_world([Completion("Hi there!")])

    await world.assistant.handle(inbound("hello"))

    sent = world.messaging.sent[-1][1].text
    assert sent.startswith("[AI assistant]: ")  # the customer sees who is answering
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+CUST")
    history = await world.deps.conversations.history(customer)
    assert history[-1].text == "Hi there!"  # stored without the prefix


async def test_assistant_stays_silent_when_the_owner_has_taken_over() -> None:
    world = build_world([Completion("the AI should not send this")])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+CUST")
    await world.customers.set_handled(customer.id, True)

    await world.assistant.handle(inbound("hello?"))

    assert world.messaging.sent == []  # the human is handling it; the AI is muted


async def test_owner_turns_reach_the_model_tagged_as_the_human_owner() -> None:
    world = build_world([Completion("Continuing where you left off!")])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+CUST")
    await world.deps.conversations.append(customer, Message(MessageRole.OWNER, "On my way!", NOW))

    await world.assistant.handle(inbound("hi again"))

    llm = world.deps.llm
    assert isinstance(llm, ScriptedLlmProvider)
    texts = [message.text for message in llm.last_messages]
    assert "[owner] On my way!" in texts  # the model sees it as the owner, not its own reply


async def test_supervisor_forces_a_lookup_when_times_offered_without_a_check() -> None:
    # The model offers times without calling find_availability (its stale-list failure mode).
    # The supervisor forces find_availability on the retry, then the model redoes the answer.
    world = build_world(
        [
            Completion("Sure! Free slots: 10:00, 11:00"),  # final draft, no tool call
            _tool("c", "find_availability", {"service": "Haircut"}),  # the forced retry call
            Completion("Here are the real times for you."),  # answered from the fresh result
        ],
        classifier=InMemoryReplyClaimClassifier({"free slots": ReplyClaim.OFFERS_TIMES}),
    )

    await world.assistant.handle(inbound("when are you free tomorrow?"))

    assert "real times" in world.messaging.sent[-1][1].text  # corrected reply, not the stale draft
    llm = world.deps.llm
    assert isinstance(llm, ScriptedLlmProvider)
    assert llm.tool_choices == [None, "find_availability", None]  # the retry was forced
    assert llm.calls == 3


async def test_supervisor_allows_times_after_a_real_availability_check() -> None:
    # When find_availability WAS called, offering times is legitimate: the supervisor still
    # classifies the draft, but the claim is backed by the tool call, so there is no rerun.
    classifier = InMemoryReplyClaimClassifier({"free slots": ReplyClaim.OFFERS_TIMES})
    world = build_world(
        [
            Completion(None, (ToolCall("c1", "find_availability", {"service": "Haircut"}),)),
            Completion("Sure! Free slots: 10:00, 11:00"),  # offered after a real check
        ],
        classifier=classifier,
    )

    await world.assistant.handle(inbound("when are you free tomorrow?"))

    assert "Free slots: 10:00, 11:00" in world.messaging.sent[-1][1].text
    llm = world.deps.llm
    assert isinstance(llm, ScriptedLlmProvider)
    assert llm.calls == 2  # no corrective third call
    assert llm.tool_choices == [None, None]  # nothing forced — the claim was backed


async def test_supervisor_forces_a_lookup_when_appointments_listed_without_one() -> None:
    # The model recites the customer's appointments from memory (the phantom-summary bug).
    # The supervisor forces find_my_appointments on the retry, then the model redoes the recap.
    world = build_world(
        [
            Completion("You have 3 appointments: ..."),  # listed from memory, no tool call
            _tool("c", "find_my_appointments", {}),  # the forced retry call
            Completion("Here is your real schedule."),  # answered from the fresh result
        ],
        classifier=InMemoryReplyClaimClassifier({"appointments": ReplyClaim.LISTS_APPOINTMENTS}),
    )

    await world.assistant.handle(inbound("what are my appointments?"))

    assert "real schedule" in world.messaging.sent[-1][1].text
    llm = world.deps.llm
    assert isinstance(llm, ScriptedLlmProvider)
    assert llm.tool_choices == [None, "find_my_appointments", None]
    assert llm.calls == 3


async def test_supervisor_reruns_when_booking_claimed_without_acting() -> None:
    # The model says a booking is done but never called book (the phantom-booking bug). A booking
    # claim can't be auto-acted, so it is instructed (no forced tool) to act or recant.
    world = build_world(
        [
            Completion("Done, you're booked!"),  # claims a booking, no tool call
            Completion("Sorry — that is not booked yet."),  # recanted on the retry
        ],
        classifier=InMemoryReplyClaimClassifier({"you're booked": ReplyClaim.CONFIRMS_BOOKING}),
    )

    await world.assistant.handle(inbound("book it"))

    assert "not booked" in world.messaging.sent[-1][1].text
    llm = world.deps.llm
    assert isinstance(llm, ScriptedLlmProvider)
    assert "did NOT call book" in llm.last_system  # instructed to act or recant
    assert llm.tool_choices == [None, None]  # a booking claim is never auto-forced
    assert llm.calls == 2
