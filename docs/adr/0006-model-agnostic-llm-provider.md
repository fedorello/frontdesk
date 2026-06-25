# ADR-0006: Model-agnostic LLM provider

**Status:** Accepted

## Context

The assistant needs a capable model, but tying the product to one vendor is a
liability: prices change, a provider has an outage, a self-hoster wants a local
model, and a business may have its own preference for cost or data residency. Vendor
SDKs also drag heavy, fast-moving dependencies into the core.

## Decision

Define one normalized **`LlmProvider`** port (a chat/tool-use call in, a normalized
completion out) and implement each vendor as an **adapter** that calls the HTTP API
directly over an injected `httpx` client — **no vendor SDKs**. Anthropic, OpenAI, and
any OpenAI-compatible endpoint (OpenRouter, a local server) are adapters. The chosen
provider and model are configuration.

## Consequences

- Swapping or adding a model is a config change plus, at most, one adapter — the core
  never changes.
- Tests run against a deterministic fake provider; no live calls, no API keys in CI.
- We own the request/response mapping, so provider quirks stay in the adapter. This
  mirrors the approach proven in Airlock.
