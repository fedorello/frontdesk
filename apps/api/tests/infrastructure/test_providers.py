"""The LLM provider adapters build the right request and parse recorded replies.

No live calls or API keys — httpx.MockTransport returns recorded responses.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from frontdesk.application.ports import Completion, LlmProvider, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.openai import OpenAiProvider

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_openai_parses_plain_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "We're open 9-17."}}]})

    provider: LlmProvider = OpenAiProvider(api_key="k", model="gpt", client=_client(handler))
    result = await provider.complete(system="s", messages=[], tools=[])

    assert result == Completion("We're open 9-17.")


async def test_openai_builds_request_and_parses_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer secret"
        assert body["model"] == "gpt"
        assert body["max_tokens"] == 2048  # reasoning models need room before the tool call
        assert body["messages"][0] == {"role": "system", "content": "be brief"}
        assert body["messages"][1] == {"role": "user", "content": "hi"}
        assert body["tools"][0]["function"]["name"] == "book"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "function": {
                                        "name": "book",
                                        "arguments": '{"service": "Haircut"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    provider = OpenAiProvider(api_key="secret", model="gpt", client=_client(handler))
    result = await provider.complete(
        system="be brief",
        messages=[Message(MessageRole.CUSTOMER, "hi", NOW)],
        tools=[ToolSpec("book", "Book it", {"type": "object"})],
    )

    assert result.text is None
    assert result.tool_calls[0].name == "book"
    assert result.tool_calls[0].args == {"service": "Haircut"}


async def test_anthropic_builds_request_and_parses_blocks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["x-api-key"] == "secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert body["system"] == "be brief"
        # the tool result is mapped to a user tool_result block
        assert body["messages"][0]["content"][0]["type"] == "tool_result"
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "Sure!"},
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "find_availability",
                        "input": {"service": "Haircut"},
                    },
                ]
            },
        )

    provider: LlmProvider = AnthropicProvider(
        api_key="secret", model="claude", client=_client(handler)
    )
    result = await provider.complete(
        system="be brief",
        messages=[Message(MessageRole.TOOL, "result text", NOW, tool_call_id="t1")],
        tools=[ToolSpec("find_availability", "Find slots", {"type": "object"})],
    )

    assert result.text == "Sure!"
    assert result.tool_calls[0].name == "find_availability"
    assert result.tool_calls[0].args == {"service": "Haircut"}


async def test_message_roles_are_mapped_per_provider() -> None:
    messages = [
        Message(MessageRole.CUSTOMER, "hi", NOW),
        Message(MessageRole.ASSISTANT, "sure", NOW),
        Message(MessageRole.TOOL, "result", NOW, tool_call_id="t1"),
    ]

    def openai_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert [m["role"] for m in body["messages"]] == ["system", "user", "assistant", "tool"]
        assert body["messages"][3]["tool_call_id"] == "t1"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    await OpenAiProvider(api_key="k", model="m", client=_client(openai_handler)).complete(
        system="s", messages=messages, tools=[]
    )

    def anthropic_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    await AnthropicProvider(api_key="k", model="m", client=_client(anthropic_handler)).complete(
        system="s", messages=messages, tools=[]
    )
