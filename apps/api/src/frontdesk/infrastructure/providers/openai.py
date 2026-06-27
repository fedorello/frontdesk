"""OpenAI-compatible chat-completions adapter (OpenAI, OpenRouter, local)."""

import json
from collections.abc import Sequence

import httpx

from frontdesk.application.ports import Completion, ToolCall, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message

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
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")
        # Reasoning models spend tokens thinking before the tool call; a small
        # budget truncates (finish_reason="length") before the call is emitted.
        self._max_tokens = max_tokens

    async def complete(
        self, *, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> Completion:
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
        return Completion(text=message.get("content"), tool_calls=tool_calls)
