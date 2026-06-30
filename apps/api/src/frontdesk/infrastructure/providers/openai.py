"""OpenAI-compatible chat-completions adapter (OpenAI, OpenRouter, local)."""

import json
import logging
from collections.abc import Sequence

import httpx

from frontdesk.application.ports import Completion, ToolCall, ToolSpec
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

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> Completion:
        wire_messages: list[dict[str, object]] = [
            {"role": "system", "content": system},
            *(_to_message(message) for message in messages),
        ]
        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": wire_messages,
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
        if self._log_prompts:
            _logger.info(
                "LLM REQUEST model=%s\n--- system ---\n%s\n--- messages ---\n%s\n--- tools ---\n%s",
                self._model,
                system,
                "\n".join(f"[{m['role']}] {m['content']}" for m in wire_messages[1:]),
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
