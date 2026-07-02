"""OpenAI-compatible chat-completions adapter (OpenAI, OpenRouter, local)."""

import json
import logging
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from frontdesk.application.ports import Completion, StreamChunk, ToolCall, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message

_logger = logging.getLogger("frontdesk.llm")

_ROLE = {
    MessageRole.CUSTOMER: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.OWNER: "assistant",  # owner replies are business-side, like the assistant's
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
}


def _to_message(message: Message) -> dict[str, object]:
    payload: dict[str, object] = {"role": _ROLE[message.role], "content": message.text}
    if message.role is MessageRole.TOOL:
        payload["tool_call_id"] = message.tool_call_id or ""
    if message.tool_calls:
        # Declare the assistant's calls so a following tool result is valid for strict providers.
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in message.tool_calls
        ]
    return payload


@dataclass
class _ToolFragment:
    """Accumulates a streamed tool call, whose id/name/arguments arrive across many SSE deltas."""

    id: str = ""
    name: str = ""
    arguments: str = ""


# The chat-completions wire is dynamic JSON, so these parsers work in Any.
def _stream_delta(line: str) -> dict[str, Any] | None:
    """The ``delta`` object of one SSE line, or None for blanks, ``[DONE]``, and non-data lines."""
    if not line.startswith("data: "):
        return None
    data = line[len("data: ") :]
    if data == "[DONE]":
        return None
    choices = json.loads(data).get("choices") or [{}]
    delta = choices[0].get("delta")
    return delta if isinstance(delta, dict) else None


def _merge_tool_fragment(fragments: dict[int, _ToolFragment], raw: dict[str, Any]) -> None:
    """Fold one streamed tool-call delta into the fragment for its index."""
    fragment = fragments.setdefault(raw.get("index", 0), _ToolFragment())
    if raw.get("id"):
        fragment.id = raw["id"]
    function = raw.get("function") or {}
    if function.get("name"):
        fragment.name = function["name"]
    if function.get("arguments"):
        fragment.arguments += function["arguments"]


def _assemble(text_parts: list[str], fragments: dict[int, _ToolFragment]) -> Completion:
    tool_calls = tuple(
        ToolCall(f.id, f.name, json.loads(f.arguments or "{}")) for f in fragments.values()
    )
    return Completion(text="".join(text_parts) or None, tool_calls=tool_calls)


class OpenAiProvider:
    """Calls a `/chat/completions` endpoint and normalizes the reply."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
        base_url: str = "https://api.openai.com/v1",
        max_tokens: int = 2048,
        log_prompts: bool = False,
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")
        # Reasoning models spend tokens thinking before the tool call; a small
        # budget truncates (finish_reason="length") before the call is emitted.
        self._max_tokens = max_tokens
        # Diagnostic: log the exact prompt sent and the reply (incl. whether a tool was called).
        self._log_prompts = log_prompts

    def _payload(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system},
                *(_to_message(message) for message in messages),
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ],
        }
        if tool_choice is not None:
            payload["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}
        return payload

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> Completion:
        payload = self._payload(system, messages, tools, tool_choice)
        if self._log_prompts:
            _logger.info(
                "LLM REQUEST model=%s\n--- system ---\n%s\n--- messages ---\n%s\n--- tools ---\n%s",
                self._model,
                system,
                "\n".join(f"[{message.role.value}] {message.text}" for message in messages),
                ", ".join(tool.name for tool in tools),
            )
        response = await self._client.post(
            f"{self._base}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self._key}"},
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        tool_calls = tuple(
            ToolCall(
                call["id"],
                call["function"]["name"],
                json.loads(call["function"]["arguments"] or "{}"),
            )
            for call in message.get("tool_calls") or []
        )
        if self._log_prompts:
            _logger.info(
                "LLM REPLY text=%r tool_calls=%s",
                message.get("content"),
                [(c.name, c.args) for c in tool_calls],
            )
        return Completion(text=message.get("content"), tool_calls=tool_calls)

    async def complete_stream(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        payload = {**self._payload(system, messages, tools, tool_choice), "stream": True}
        if self._log_prompts:
            _logger.info(
                "LLM REQUEST (stream) model=%s\n--- system ---\n%s\n--- messages ---\n%s"
                "\n--- tools ---\n%s",
                self._model,
                system,
                "\n".join(f"[{message.role.value}] {message.text}" for message in messages),
                ", ".join(tool.name for tool in tools),
            )
        text_parts: list[str] = []
        fragments: dict[int, _ToolFragment] = {}
        async with self._client.stream(
            "POST",
            f"{self._base}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self._key}"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                delta = _stream_delta(line)
                if delta is None:
                    continue
                if content := delta.get("content"):
                    text_parts.append(content)
                    yield StreamChunk(text_delta=content)
                for raw in delta.get("tool_calls") or []:
                    _merge_tool_fragment(fragments, raw)
        completion = _assemble(text_parts, fragments)
        if self._log_prompts:
            _logger.info(
                "LLM REPLY (stream) text=%r tool_calls=%s",
                completion.text,
                [(c.name, c.args) for c in completion.tool_calls],
            )
        yield StreamChunk(completion=completion)
