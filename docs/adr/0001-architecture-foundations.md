# ADR-0001: Architecture foundations

**Status:** Accepted

## Context

Frontdesk is a real product: an AI assistant that takes customer messages, books
appointments, and sends reminders for small service businesses. It must talk to
several channels (WhatsApp, Telegram), several LLM providers, a database, and a
scheduler — and still be testable, readable, and safe to change. The temptation in
"AI apps" is to weld the model, the framework, and the integrations into one ball
of glue code that can't be tested or reasoned about.

## Decision

Build the core with **hexagonal architecture (ports & adapters)** and dependency
injection:

- A pure **domain** (entities and business rules) that imports no framework, no
  database, no HTTP, and no LLM.
- An **application** layer of use cases and **ports** (Python `Protocol`s).
- **Infrastructure** adapters at the edges (channels, DB, LLM, Redis), each with
  an in-memory **fake** for tests.
- A thin **interface** layer (FastAPI routers, the worker).

The backend is **Python** (FastAPI); the admin **dashboard** is **Next.js**. Tests
are fast and deterministic — no live API calls (LLM, messaging, or DB) in unit
tests. import-linter enforces the inward dependency rule in CI.

## Consequences

- Adding a channel, a model, or a calendar backend is a new adapter, not a rewrite.
- The business logic is testable without a network, hitting ≥ 90% coverage in the
  core (per `CODING_PRINCIPLES.md`).
- There is upfront structure (ports, fakes) that a quick script wouldn't have —
  accepted deliberately; it is what makes the product maintainable.
