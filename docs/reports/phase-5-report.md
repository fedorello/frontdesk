# Phase 5 — LLM provider adapters — report

**Status:** Done (2026-06-25)

## What was built (`infrastructure/providers/`)

- `openai.py` — `OpenAiProvider`: calls a `/chat/completions` endpoint (OpenAI,
  OpenRouter, or a local OpenAI-compatible server) over an injected `httpx`
  client, maps domain messages to the API shape (system/user/assistant/tool with
  `tool_call_id`), sends the tool specs, and normalizes the reply (text +
  `tool_calls`) to `Completion`.
- `anthropic.py` — `AnthropicProvider`: the Anthropic Messages API (text +
  `tool_use` blocks → `Completion`; tool results mapped to `tool_result` blocks),
  also over an injected `httpx` client. No vendor SDKs.

## Verification

- **Recorded-response tests** (`tests/infrastructure/test_providers.py`,
  `logs/phase-5/check.log`): each adapter is exercised through the **real httpx
  request/response cycle** via `httpx.MockTransport` — no live calls, no keys (so
  it is CI-safe). The tests assert the request shape (model, headers, system,
  message roles, tools) and the parsing of both a plain-text reply and a tool
  call. **100 % coverage** on both adapters; 79 tests, 97.4 % overall; gate green.
- Swapping providers is config-only — both satisfy the `LlmProvider` port (mypy
  confirms structural conformance).

## Live run (real model, logged to `logs/phase-5/live-run.log`)

Against **`deepseek/deepseek-v4-flash` via OpenRouter** (OpenAI-compatible, through
`OpenAiProvider` — config-only, no code change):

- A single `complete()` call returned text **plus a real tool call**
  (`find_availability(service="haircut")`), parsed correctly into a `Completion`.
- The **full Phase 3 assistant loop, unchanged**, handled "Can I book a Haircut for
  1pm?": the live model ran the multi-turn tool flow (`find_availability` → `book`),
  the typed core **booked a real appointment** (`ap-1`, 13:00 UTC, status pending),
  and `MessageReceived` + `AppointmentBooked` were published.

(Note: a reranker/vision model like `nvidia/llama-nemotron-rerank-vl-1b-v2` returns
"no endpoints support tool use" — the adapter surfaced that error correctly; a
tool-capable chat model such as deepseek-v4-flash is required.)

## Definition of Done

- [x] Anthropic and OpenAI(-compatible) adapters over httpx, no SDK.
- [x] Adapter tests against recorded responses (no live keys in CI).
- [x] The assistant loop runs unchanged against a real provider locally.
