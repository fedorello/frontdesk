# Implementation plan

A phased, reviewed build of Frontdesk. The order is **inside-out**: the pure
domain first, then ports and fakes, then use cases tested against those fakes,
then the real edges (database, LLM, channels), then the worker and the dashboard,
then CI and evals. Every phase ends green against the gate in
[`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md) and the contracts in
[`docs/design/contracts.md`](../design/contracts.md).

## Status

| Phase | Title                                   | Status      |
| ----- | --------------------------------------- | ----------- |
| 0     | Scaffold & gates                        | ✅ Done — [report](../reports/phase-0-report.md) |
| 1     | Domain core                             | ✅ Done — [report](../reports/phase-1-report.md) |
| 2     | Ports & in-memory fakes                 | ✅ Done — [report](../reports/phase-2-report.md) |
| 3     | Use cases & the assistant loop          | ✅ Done — [report](../reports/phase-3-report.md) |
| 4     | Persistence (PostgreSQL)                | 🚧 In progress — deps + async engine + test split |
| 5     | LLM provider adapters                   | Not started |
| 6     | Channels & webhooks                     | Not started |
| 7     | Worker (reminders) & the approval gate  | Not started |
| 8     | Admin dashboard                         | Not started |
| 9     | CI/CD, evals & release readiness        | Not started |

## Phase 0 — Scaffold & gates

**Goal:** an empty but fully-gated `apps/api`, so every later phase lands on green
rails.

- `uv` project, the hexagonal package skeleton (`domain/ application/ infrastructure/
  interface/ core/`), `Settings` (pydantic-settings), composition root.
- Tooling: ruff, mypy (`--strict`), import-linter contracts (inward dependencies),
  pytest + coverage.
- `deploy/` Docker Compose (postgres, redis) and a `Makefile` (`up`, `down`, `test`,
  `lint`, `fmt`, `check`).

**DoD:** `make check` runs ruff + mypy + import-linter + pytest and passes on an
empty skeleton; Compose brings up Postgres and Redis.

## Phase 1 — Domain core

**Goal:** the pure business rules, no I/O.

- Entities, value objects, enums, ids, and domain errors per the contracts.
- Availability math (working hours − buffer − existing appointments − lead time →
  free slots), booking rules, and both state machines (appointment, reminder) as
  pure functions/objects.

**DoD:** unit tests cover the rules and every state transition (including rejected
ones) to ≥ 90%; the package imports nothing from the stack; import-linter green.

## Phase 2 — Ports & in-memory fakes

**Goal:** the seams the rest of the system plugs into.

- All ports as `Protocol`s (messaging, llm, calendar, repositories, reminder store,
  event publisher, approval gate, clock, ids).
- An in-memory fake for each, plus a fixed `Clock`/`IdGenerator`.

**DoD:** a shared "port contract" test suite that any adapter (fake now, real later)
must pass; fakes pass it.

## Phase 3 — Use cases & the assistant loop

**Goal:** the application behavior, tested entirely against fakes.

- `BookAppointment`, `RescheduleAppointment`, `CancelAppointment`, `SendDueReminders`.
- `HandleInboundMessage` — the tool-use loop with the assistant's tools, run against
  a **scripted fake `LlmProvider`** so it is deterministic.

**DoD:** the three flows (answer, booking, reminder) pass end-to-end against fakes;
grounding and escalation are tested (no invented slots/prices); no live calls.

## Phase 4 — Persistence (PostgreSQL)

**Goal:** durable state behind the repository and calendar ports.

- SQLAlchemy 2.0 (async) models + Alembic migrations for the schema in the contracts,
  including a migration that enables the `btree_gist` extension, the **no-double-book
  exclusion constraint**, and the reminder index.
- Repository, `Calendar`, and `ReminderStore` adapters.

**DoD:** the adapters pass the same port-contract suite as the fakes, **plus**
integration tests on a real Postgres (double-book rejected, `claim_due` with
`SKIP LOCKED` never double-claims, tenant isolation holds).

## Phase 5 — LLM provider adapters

**Goal:** real models behind `LlmProvider`, no SDK.

- Anthropic and OpenAI(-compatible) adapters over an injected `httpx` client;
  request/response normalization to `Completion`.

**DoD:** adapter tests against recorded responses (no live keys in CI); swapping
provider is config-only; the Phase 3 loop runs unchanged on a real provider locally.

## Phase 6 — Channels & webhooks

**Goal:** customers can actually reach the assistant.

- WhatsApp Cloud API adapter + webhook (signature verify, idempotency, normalize),
  then Telegram Bot API adapter + webhook.
- Tenant resolution from the channel binding.

**DoD:** an inbound message → reply runs end-to-end against a fake HTTP layer;
webhook signature and idempotency are tested; the messaging adapters pass the port
contract.

## Phase 7 — Worker (reminders) & the approval gate

**Goal:** no-shows actually get reminded; sensitive actions are gated.

- The worker process: a ~1-minute loop calling `SendDueReminders` (Postgres polling,
  `SKIP LOCKED`); reminders scheduled on booking, cancelled on cancel/move.
- Wire `airlock-hitl` as the `ApprovalGate`; sensitive tools pause for approval.

**DoD:** reminders fire reliably and exactly once across a restart and with two
workers; a gated action pauses and only runs after approval — both covered by tests.

## Phase 8 — Admin dashboard

**Goal:** the business owner can see and run everything.

- `apps/dashboard` (Next.js 16): calendar, conversations, settings (services, hours,
  knowledge base, channels), and the **approvals** inbox (the gate). Live updates via
  the Redis event stream.

**DoD:** the dashboard's own gate (typecheck, lint, test, build) is green; a Playwright
e2e covers viewing the calendar and approving a pending action.

## Phase 9 — CI/CD, evals & release readiness

**Goal:** trustworthy and shippable.

- GitHub Actions running the full backend gate and the dashboard gate on every push,
  with Postgres/Redis services for integration tests.
- An **eval suite** for the assistant: realistic conversations asserting it books the
  right slot, never invents availability/prices, reminds, and escalates correctly.
- README quickstart, a one-command demo (`make up`), and a seeded example business.

**DoD:** CI green across backend + dashboard; evals pass; `make up` brings the whole
product up locally with a demo business and a working WhatsApp/Telegram sandbox path.

## Out of scope (for now)

Payments/POS integration beyond refunds, marketing campaigns, multi-language NLU
tuning, and external calendar two-way sync (Google/Outlook) are deliberately deferred
until the core loop is proven.
