# Documentation

How the Frontdesk docs are organized. Keep this index in sync.

## Using it

- [`usage.md`](./usage.md) — **start here**: what it does, how it works, and how to
  run, try, configure, and extend it.
- [`configuration.md`](./configuration.md) — every `FRONTDESK_*` environment
  variable, with defaults.
- [`api.md`](./api.md) — the HTTP API: web chat, approvals inbox, channel webhooks.

## How it's built

- [`stack.md`](./stack.md) — the technology stack and pinned versions (verified
  2026-06-25).
- [`architecture/overview.md`](./architecture/overview.md) — the full architecture:
  the hexagon, the domain model, the ports & adapters, and the three flows
  (answer, booking, reminder).
- [`design/contracts.md`](./design/contracts.md) — the precise contract: domain
  types, ports, use cases, the assistant's tools, state machines, invariants, the
  database schema, and the errors.
- [`plans/implementation-plan.md`](./plans/implementation-plan.md) — the phased,
  inside-out build with a status snapshot and a Definition of Done per phase.

## SaaS direction (multi-tenant, Telegram-first, multilingual)

- [`plans/saas-telegram-plan.md`](./plans/saas-telegram-plan.md) — the phased plan to
  turn Frontdesk into a self-serve SaaS.
- [`design/ux-brief.md`](./design/ux-brief.md) — the UI/UX brief for the dashboard
  (what screens are needed; hand to a designer).

## Architecture Decision Records (`adr/`)

- [0001 — Architecture foundations](./adr/0001-architecture-foundations.md) —
  hexagonal, DI, Python core + Next.js dashboard, deterministic tests.
- [0002 — Channels behind a messaging port](./adr/0002-channels-behind-a-messaging-port.md)
  — WhatsApp Cloud API + Telegram Bot API as adapters.
- [0003 — Multi-tenant by business](./adr/0003-multi-tenant-by-business.md) —
  one deployment, many businesses, strict isolation.
- [0004 — Durable reminders in PostgreSQL](./adr/0004-durable-reminders-in-postgres.md)
  — a Postgres-backed scheduled-job table + polling worker, no external queue.
- [0005 — Human-in-the-loop via Airlock](./adr/0005-human-in-the-loop-via-airlock.md)
  — sensitive actions pass an approval gate (`airlock-hitl`).
- [0006 — Model-agnostic LLM provider](./adr/0006-model-agnostic-llm-provider.md) —
  one port, one adapter per vendor, HTTP (no SDK).
- [0007 — The assistant is a tool-use agent](./adr/0007-assistant-as-tool-use-agent.md)
  — the model decides intent; the typed core decides what actually happens.
- [0008 — Multi-tenant self-serve SaaS](./adr/0008-multi-tenant-self-serve-saas.md) —
  per-tenant Telegram bots, self-serve onboarding, multilingual; Telegram-first.
