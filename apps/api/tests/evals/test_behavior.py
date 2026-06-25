"""Behavioral evals: the guardrails that matter, on realistic conversations.

These are deterministic (the scripted provider stands in for the model) so they
run in the gate and in CI. A live-model variant lives in ``scripts/eval_live.py``
and is run locally against a real provider. The properties asserted here are the
ones the product lives or dies on: it books the *real* slot, it never invents
availability or prices, it reminds, and it escalates instead of guessing.
"""

from frontdesk.application.ports import Completion, Escalated, ToolCall
from tests.application.world import build_world, inbound


def _tool(call_id: str, name: str, args: dict[str, object]) -> Completion:
    return Completion(None, (ToolCall(call_id, name, args),))


async def test_books_the_exact_slot_the_customer_asked_for() -> None:
    world = build_world(
        [
            _tool("1", "find_availability", {"service": "Haircut"}),
            _tool("2", "book", {"service": "Haircut", "start": "2026-06-26T15:00:00+00:00"}),
            Completion("You're booked for 3pm!"),
        ]
    )

    await world.assistant.handle(inbound("can I get a haircut at 3pm tomorrow?"))

    appointments = list(world.appointments.appointments.values())
    assert len(appointments) == 1
    assert appointments[0].slot.starts_at.isoformat() == "2026-06-26T15:00:00+00:00"


async def test_never_invents_availability_outside_working_hours() -> None:
    # The model attempts a 03:00 booking, well outside 09:00-17:00. The typed
    # core must refuse; no appointment may be created from a hallucinated slot.
    world = build_world(
        [
            _tool("1", "book", {"service": "Haircut", "start": "2026-06-26T03:00:00+00:00"}),
            Completion("Sorry, 3am isn't available — we're open 9 to 17."),
        ]
    )

    await world.assistant.handle(inbound("book me a haircut at 3am"))

    assert world.appointments.appointments == {}  # nothing booked


async def test_never_invents_prices_answers_only_from_knowledge() -> None:
    world = build_world([])

    grounded = world.assistant._lookup_answer(world.business, "hours")
    invented = world.assistant._lookup_answer(world.business, "price of a nose job")

    assert "9 to 17" in grounded
    assert "don't have that information" in invented


async def test_a_booking_schedules_a_reminder() -> None:
    world = build_world(
        [
            _tool("1", "book", {"service": "Haircut", "start": "2026-06-26T15:00:00+00:00"}),
            Completion("Done — see you then!"),
        ]
    )

    await world.assistant.handle(inbound("book a haircut for 3pm"))

    assert len(world.reminders.reminders) >= 1


async def test_escalates_instead_of_guessing() -> None:
    world = build_world(
        [
            _tool("1", "escalate", {"reason": "angry customer with a complaint"}),
            Completion("I'm sorry about that — a colleague will follow up shortly."),
        ]
    )

    await world.assistant.handle(inbound("this is unacceptable, I want to complain!"))

    assert any(isinstance(event, Escalated) for event in world.events.events)
