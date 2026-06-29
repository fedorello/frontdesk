"""The recorder writes each LLM turn to its own file and never breaks the turn on a write error."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from frontdesk.application.ports import Completion, ToolCall, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message
from frontdesk.infrastructure.llm_recorder import RecordingLlmProvider
from frontdesk.infrastructure.system import FixedClock

NOW = datetime(2026, 6, 29, 3, 27, 5, tzinfo=UTC)


class _StubLlm:
    def __init__(self, completion: Completion) -> None:
        self.completion = completion

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> Completion:
        return self.completion


async def test_records_each_turn_to_its_own_file(tmp_path: Path) -> None:
    inner = _StubLlm(Completion("Booked!", (ToolCall("c", "book", {"start": "x"}),)))
    recorder = RecordingLlmProvider(inner, tmp_path, FixedClock(NOW))

    result = await recorder.complete(
        system="You are a bot",
        messages=[Message(MessageRole.CUSTOMER, "book me", NOW)],
        tools=[ToolSpec("book", "Book a slot", {})],
        tool_choice="book",
    )

    assert result.text == "Booked!"  # the inner result passes straight through
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1  # one file for the one turn
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["system"] == "You are a bot"
    assert record["tool_choice"] == "book"
    assert record["messages"][0]["text"] == "book me"
    assert record["tools"] == ["book"]
    assert record["response"]["tool_calls"][0]["name"] == "book"


async def test_a_write_failure_does_not_break_the_turn(tmp_path: Path) -> None:
    # The target dir's parent is a FILE, so mkdir raises — the turn must still return its reply.
    blocker = tmp_path / "blocked"
    blocker.write_text("x")
    recorder = RecordingLlmProvider(_StubLlm(Completion("ok")), blocker / "sub", FixedClock(NOW))

    result = await recorder.complete(system="s", messages=[], tools=[], tool_choice=None)

    assert result.text == "ok"  # the OSError was swallowed
    assert not (blocker / "sub").exists()
