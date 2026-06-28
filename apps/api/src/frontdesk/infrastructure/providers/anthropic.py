"""Anthropic Messages API adapter (HTTP, no SDK)."""

from collections.abc import Sequence

import httpx

from frontdesk.application.ports import Completion, ToolCall, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message

_ANTHROPIC_VERSION = "2023-06-01"


def _to_message(message: Message) -> dict[str, object]:
    if message.role is MessageRole.TOOL:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id or "",
                    "content": message.text,
                }
            ],
        }
    # Owner replies are business-side, so the model sees them as assistant turns.
    business_side = {MessageRole.ASSISTANT, MessageRole.OWNER}
    role = "assistant" if message.role in business_side else "user"
    return {"role": role, "content": message.text}


class AnthropicProvider:
    """Calls the Anthropic Messages API and normalizes the reply."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int = 2048,
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")
        self._max_tokens = max_tokens

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        tool_choice: str | None = None,
    ) -> Completion:
        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [_to_message(message) for message in messages],
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ],
        }
        if tool_choice is not None:
            payload["tool_choice"] = {"type": "tool", "name": tool_choice}
        response = await self._client.post(
            f"{self._base}/v1/messages",
            json=payload,
            headers={"x-api-key": self._key, "anthropic-version": _ANTHROPIC_VERSION},
        )
        response.raise_for_status()
        blocks = response.json()["content"]
        text = next((block["text"] for block in blocks if block["type"] == "text"), None)
        tool_calls = tuple(
            ToolCall(block["id"], block["name"], block["input"])
            for block in blocks
            if block["type"] == "tool_use"
        )
        return Completion(text=text, tool_calls=tool_calls)
