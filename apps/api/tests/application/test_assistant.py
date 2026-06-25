"""The assistant loop: the answer, booking, and escalation flows end-to-end."""

from frontdesk.application.assistant import ESCALATION_FALLBACK, MAX_STEPS, _system_prompt
from frontdesk.application.ports import (
    AppointmentBooked,
    ApprovalRequested,
    Completion,
    Escalated,
    InboundMessage,
    MessageReceived,
    ToolCall,
)
from frontdesk.domain.enums import AppointmentStatus, Channel
from frontdesk.domain.ids import AppointmentId
from tests.application.world import NOW, build_world, inbound


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

    assert world.messaging.sent[-1][1].text == "We're open 9 to 17, Monday to Friday."
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

    assert world.messaging.sent[-1][1].text == "You're booked!"
    appointments = list(world.appointments.appointments.values())
    assert len(appointments) == 1
    assert appointments[0].status == AppointmentStatus.PENDING
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
    assert world.messaging.sent[-1][1].text == "A team member will follow up shortly."


def test_system_prompt_lists_only_real_services() -> None:
    world = build_world([])

    prompt = _system_prompt(world.business, [world.service])

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

    assert world.messaging.sent[-1][1].text == ESCALATION_FALLBACK


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
    assert world.messaging.sent[-1][1].text == "All sorted!"


async def test_find_availability_reports_unknown_service() -> None:
    world = build_world(
        [
            _tool("1", "find_availability", {"service": "Massage"}),
            Completion("Sorry, we don't offer that yet."),
        ]
    )

    await world.assistant.handle(inbound("do you do massages?"))

    assert world.messaging.sent[-1][1].text == "Sorry, we don't offer that yet."


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
