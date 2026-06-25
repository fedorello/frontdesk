# Phase 5 — LLM provider adapters — report

**Status:** In progress — adapters done + recorded-response tested; the live-model
run is pending an API key.

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

## Pending

- **The live run** — one real call to a hosted model to confirm the assistant
  works end-to-end against an actual LLM — needs a real API key (Anthropic,
  OpenAI, or OpenRouter). It will be run and logged once the key is provided.

## Definition of Done

- [x] Anthropic and OpenAI(-compatible) adapters over httpx, no SDK.
- [x] Adapter tests against recorded responses (no live keys in CI).
- [ ] The assistant loop runs against a real provider locally (needs an API key).
