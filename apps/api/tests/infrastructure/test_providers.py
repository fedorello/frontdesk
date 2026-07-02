"""The LLM provider adapters build the right request and parse recorded replies.

No live calls or API keys — httpx.MockTransport returns recorded responses.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from frontdesk.application.ports import Completion, LlmProvider, ReplyClaim, ToolSpec
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.models import Message, ToolCallRef
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.groq import (
    GroqReplyClaimClassifier,
    NullReplyClaimClassifier,
)
from frontdesk.infrastructure.providers.openai import OpenAiProvider

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
Handler = Callable[[httpx.Request], httpx.Response]
_GROQ_BASE = "https://api.groq.com/openai/v1"


def _classifier(handler: Handler) -> GroqReplyClaimClassifier:
    return GroqReplyClaimClassifier(
        api_key="gk", model="llama-3.1-8b-instant", client=_client(handler), base_url=_GROQ_BASE
    )


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_openai_parses_plain_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "We're open 9-17."}}]})

    provider: LlmProvider = OpenAiProvider(api_key="k", model="gpt", client=_client(handler))
    result = await provider.complete(system="s", messages=[], tools=[])

    assert result == Completion("We're open 9-17.")


async def test_openai_serializes_assistant_tool_calls_with_the_tool_result() -> None:
    # Strict providers (Groq) require a tool result to follow an assistant turn that declares the
    # matching call; the assistant Message must serialize its tool_calls.
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["messages"] = json.loads(request.content)["messages"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "done"}}]})

    provider: LlmProvider = OpenAiProvider(api_key="k", model="gpt", client=_client(handler))
    history = [
        Message(MessageRole.CUSTOMER, "book friday", NOW),
        Message(
            MessageRole.ASSISTANT,
            "checking",
            NOW,
            tool_calls=(ToolCallRef("c1", "find_availability", '{"service": "Haircut"}'),),
        ),
        Message(MessageRole.TOOL, "Free slots: ...", NOW, tool_call_id="c1"),
    ]

    await provider.complete(system="s", messages=history, tools=[])

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[2]["tool_calls"] == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "find_availability", "arguments": '{"service": "Haircut"}'},
        }
    ]
    assert messages[3] == {"role": "tool", "content": "Free slots: ...", "tool_call_id": "c1"}


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


async def test_openai_streams_text_deltas_then_a_final_completion() -> None:
    events = [
        {"choices": [{"delta": {"content": "Let me "}}]},
        {"choices": [{"delta": {"content": "check."}}]},
        # a tool call whose name + arguments arrive split across two deltas
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {"index": 0, "id": "c1", "function": {"name": "find_availability"}}
                        ]
                    }
                }
            ]
        },
        {
            "choices": [
                {"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"x": 1}'}}]}}
            ]
        },
    ]
    body = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = OpenAiProvider(api_key="k", model="gpt", client=_client(handler))
    chunks = [chunk async for chunk in provider.complete_stream(system="s", messages=[], tools=[])]

    assert [c.text_delta for c in chunks if c.text_delta] == ["Let me ", "check."]
    final = chunks[-1].completion
    assert final is not None
    assert final.text == "Let me check."  # deltas reassembled
    assert final.tool_calls[0].name == "find_availability"  # accumulated across deltas
    assert final.tool_calls[0].args == {"x": 1}


async def test_anthropic_streams_a_single_buffered_chunk() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "We're open 9-17."}]})

    provider: LlmProvider = AnthropicProvider(api_key="k", model="claude", client=_client(handler))
    chunks = [chunk async for chunk in provider.complete_stream(system="s", messages=[], tools=[])]

    assert [c.text_delta for c in chunks if c.text_delta] == ["We're open 9-17."]
    assert chunks[-1].completion == Completion("We're open 9-17.")


async def test_google_credential_verifier_accepts_a_valid_token() -> None:
    from frontdesk.infrastructure.google_oauth import HttpGoogleCredentialVerifier

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id_token"] == "cred"
        return httpx.Response(
            200,
            json={
                "aud": "my-client",
                "iss": "https://accounts.google.com",
                "email": "caller@example.com",
                "email_verified": "true",
                "name": "Caller",
            },
        )

    identity = await HttpGoogleCredentialVerifier("my-client", _client(handler)).verify("cred")

    assert identity is not None
    assert identity.email == "caller@example.com"


async def test_google_credential_verifier_rejects_wrong_audience_and_bad_status() -> None:
    from frontdesk.infrastructure.google_oauth import HttpGoogleCredentialVerifier

    def wrong_aud(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"aud": "someone-else", "iss": "accounts.google.com", "email_verified": "true"},
        )

    def invalid(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_token"})

    assert await HttpGoogleCredentialVerifier("my-client", _client(wrong_aud)).verify("c") is None
    assert await HttpGoogleCredentialVerifier("my-client", _client(invalid)).verify("c") is None


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


async def test_groq_classifier_parses_multiple_claim_tags_and_ignores_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer gk"
        assert body["model"] == "llama-3.1-8b-instant"
        assert body["temperature"] == 0  # deterministic classification
        assert body["messages"][1]["content"] == "Booked! Earliest is 10:00."
        # LIST is no longer a tag (appointments live in the prompt) — an unknown tag is ignored.
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "TIMES BOOKING LIST"}}]}
        )

    claims = await _classifier(handler).classify("Booked! Earliest is 10:00.")
    assert claims == frozenset({ReplyClaim.OFFERS_TIMES, ReplyClaim.CONFIRMS_BOOKING})


async def test_groq_classifier_returns_empty_for_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "NONE"}}]})

    assert await _classifier(handler).classify("Thanks, talk soon!") == frozenset()


async def test_groq_classifier_skips_empty_messages_without_a_call() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"choices": [{"message": {"content": "TIMES"}}]})

    assert await _classifier(handler).classify("   ") == frozenset()
    assert called is False  # no network call for an empty draft


async def test_groq_classifier_degrades_to_empty_when_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)  # supervisor outage

    # Best-effort: an outage must not block the customer's reply.
    assert await _classifier(handler).classify("Free at 10:00?") == frozenset()


async def test_groq_fact_normalizer_cleans_a_value() -> None:
    from frontdesk.infrastructure.providers.groq import GroqFactNormalizer

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-20b"
        assert body["temperature"] == 0
        # A reasoning model needs room + shallow effort, else its thinking starves the answer.
        assert body["max_tokens"] >= 256
        assert body["reasoning_effort"] == "low"
        return httpx.Response(200, json={"choices": [{"message": {"content": "London"}}]})

    normalizer = GroqFactNormalizer(
        api_key="gk", model="openai/gpt-oss-20b", client=_client(handler), base_url=_GROQ_BASE
    )
    assert await normalizer.normalize("Birth place", "in London") == "London"


async def test_groq_fact_normalizer_keeps_the_raw_value_when_unreachable() -> None:
    from frontdesk.infrastructure.providers.groq import GroqFactNormalizer

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)  # normalizer outage must never lose the fact

    normalizer = GroqFactNormalizer(
        api_key="gk", model="llama-3.1-8b-instant", client=_client(handler), base_url=_GROQ_BASE
    )
    assert await normalizer.normalize("Birth place", "  in London  ") == "in London"


async def test_null_classifier_never_flags() -> None:
    assert await NullReplyClaimClassifier().classify("Free at 10:00?") == frozenset()


async def test_tool_choice_forces_a_specific_tool_per_provider() -> None:
    def openai_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["tool_choice"] == {
            "type": "function",
            "function": {"name": "find_availability"},
        }
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    await OpenAiProvider(api_key="k", model="m", client=_client(openai_handler)).complete(
        system="s", messages=[], tools=[], tool_choice="find_availability"
    )

    def anthropic_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["tool_choice"] == {"type": "tool", "name": "find_availability"}
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    await AnthropicProvider(api_key="k", model="m", client=_client(anthropic_handler)).complete(
        system="s", messages=[], tools=[], tool_choice="find_availability"
    )
