# Phase 2 — Ports & in-memory fakes — report

**Status:** Done (2026-06-25)

## What was built

- `application/ports.py` — every port as a `Protocol`, plus the DTOs they carry
  (`OutboundMessage`, `InboundMessage`, `ToolSpec`/`ToolCall`/`Completion`,
  `SensitiveAction`/`Decision`, and the `DomainEvent` family). Ports: `Clock`,
  `IdGenerator`, `MessagingPort`, `LlmProvider`, `Calendar`, the four repositories,
  `ReminderStore`, `EventPublisher`, `ApprovalGate`.
- `infrastructure/system.py` — `SystemClock`/`UuidIdGenerator` (real) and
  `FixedClock`/`SequentialIdGenerator` (deterministic).
- `infrastructure/memory.py` — a real, working in-memory fake for every port (not
  mocks): messaging, events, a scripted LLM, the four repositories, the reminder
  store, the calendar (availability + bookings over the domain rules, rejecting
  double-booking), and an auto-decision approval gate.

## Verification

- **Shared port-contract suite** (`tests/port_contracts.py`): reusable `check_*`
  functions that assert each stateful port's behavior — the reminder store
  (claim only due, mark-sent, cancel), the calendar (book, **double-book
  rejected**, move, cancel), and the repositories (idempotent upsert, history
  ordering/limit, not-found). The real Postgres adapters in Phase 4 will run the
  same checks.
- **The gate** (`logs/phase-2/check.log`): ruff clean, import-linter **3/3 kept**
  (adapters don't import each other; application still imports only the domain),
  mypy `--strict` green over 27 files — which also proves every fake structurally
  conforms to its port — and pytest **63 passed, 99.8 % coverage**.
- **Real run** (`logs/phase-2/fakes-run.log`): the fakes compose into a working
  `upsert customer → find availability → book → schedule reminder → claim due →
  send (with Confirm/Reschedule buttons)` flow. Output matched expectations.

## Definition of Done

- [x] All ports defined as `Protocol`s.
- [x] An in-memory fake for each, plus a fixed clock and id generator.
- [x] A shared port-contract suite that any adapter must pass; the fakes pass it.
