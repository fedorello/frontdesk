"""The voice turn (Assistant.stream): narrate each step out loud, then answer."""

from frontdesk.application.assistant import ESCALATION_FALLBACK, MAX_STEPS
from frontdesk.application.ports import Completion, ToolCall
from tests.application.world import build_world, make_customer

_BOOK_START = "2026-06-26T15:00:00+00:00"  # 15:00 today — a free slot


def _find(text: str | None) -> Completion:
    return Completion(text, (ToolCall("f", "find_availability", {"service": "Haircut"}),))


async def _spoken(world_script: list[Completion]) -> list[str]:
    # stream() yields whole sentences: it buffers the model's streamed text deltas and flushes each
    # sentence once complete. The scripted provider hands text back in halves to exercise that.
    world = build_world(world_script)
    return [line async for line in world.assistant.stream(world.business, make_customer())]


async def test_narrates_before_a_tool_then_gives_the_final_answer() -> None:
    lines = await _spoken(
        [
            _find("Sure, let me check Friday for you."),
            Completion("I have 3 PM — does that work?"),
        ]
    )

    assert lines == ["Sure, let me check Friday for you.", "I have 3 PM — does that work?"]


async def test_streams_a_multi_sentence_reply_one_sentence_at_a_time() -> None:
    # A single completion of two sentences is spoken as two units, so TTS starts on the first
    # without waiting for the whole reply.
    lines = await _spoken([Completion("First, the good news. Then the rest.")])

    assert lines == ["First, the good news.", "Then the rest."]


async def test_narrates_each_step_and_actually_books() -> None:
    world = build_world(
        [
            _find("One moment, checking availability."),
            Completion(
                "Booking that now.",
                (ToolCall("b", "book", {"service": "Haircut", "start": _BOOK_START}),),
            ),
            Completion("You're all set for 3 PM."),
        ]
    )

    lines = [line async for line in world.assistant.stream(world.business, make_customer())]

    assert lines == [
        "One moment, checking availability.",
        "Booking that now.",
        "You're all set for 3 PM.",
    ]
    assert len(world.appointments.appointments) == 1  # the booking really happened


async def test_empty_completions_fall_back_to_a_spoken_handoff() -> None:
    lines = await _spoken([Completion(None), Completion(None), Completion(None)])

    assert lines == [ESCALATION_FALLBACK["en"]]


async def test_running_out_of_steps_hands_off() -> None:
    # The model keeps calling a tool without ever speaking — after MAX_STEPS, hand off.
    lines = await _spoken([_find(None) for _ in range(MAX_STEPS)])

    assert lines == [ESCALATION_FALLBACK["en"]]
