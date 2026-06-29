"""Records each LLM turn (the exact prompt sent and the reply) to its own file, for studying
prompts offline. Wraps any LlmProvider; one file per call so a single turn can be read in
isolation. Best-effort: a write failure is logged and never breaks the conversation."""

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from frontdesk.application.ports import Clock, Completion, LlmProvider, ToolSpec
from frontdesk.domain.models import Message

_logger = logging.getLogger("frontdesk.llm_recorder")


class RecordingLlmProvider:
    """Decorates an LlmProvider, dumping each turn's full request + response to a JSON file."""

    def __init__(self, inner: LlmProvider, directory: Path, clock: Clock) -> None:
        self._inner = inner
        self._dir = directory
        self._clock = clock

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> Completion:
        completion = await self._inner.complete(
            system=system, messages=messages, tools=tools, tool_choice=tool_choice
        )
        self._record(system, messages, tools, tool_choice, completion)
        return completion

    def _record(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None,
        completion: Completion,
    ) -> None:
        now = self._clock.now()
        name = f"{now.strftime('%Y%m%dT%H%M%S_%f')}_{uuid4().hex[:6]}.json"
        record = {
            "at": now.isoformat(),
            "tool_choice": tool_choice,
            "system": system,
            "messages": [
                {
                    "role": message.role.value,
                    "text": message.text,
                    "tool_call_id": message.tool_call_id,
                }
                for message in messages
            ],
            "tools": [tool.name for tool in tools],
            "response": {
                "text": completion.text,
                "tool_calls": [
                    {"name": call.name, "args": call.args} for call in completion.tool_calls
                ],
            },
        }
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            (self._dir / name).write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as error:
            _logger.warning("could not write LLM record %s: %s", name, error)
