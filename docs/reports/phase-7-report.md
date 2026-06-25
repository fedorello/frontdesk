# Phase 7 — Worker & the approval gate — report

**Status:** Done (2026-06-25)

## What was built

- **The approval gate.** Added a sensitive `issue_refund` tool to the assistant
  that does **not** run on the model's say-so — it passes the `ApprovalGate` port.
  If the gate doesn't approve, the action is held: an `ApprovalRequested` event is
  published (for the dashboard) and the customer is told it's flagged. The
  assistant's `AssistantDeps` now carries the gate; `infrastructure/memory.py`'s
  `AutoDecisionGate` is the test adapter.
- **The worker.** `interface/worker.py`'s `ReminderWorker` drives
  `SendDueReminders` on a fixed cadence — `tick()` for one pass, `run_until(stop)`
  for the loop.

## Verification

- **The gate** (`make check`): ruff clean, import-linter 3/3, mypy `--strict`
  green over 54 files, pytest **93 passed, 97.6 %**.
- **Tests:** the sensitive refund is held when the gate doesn't approve
  (`ApprovalRequested` published, action not executed) and runs when it does; the
  worker `tick` sends due reminders with the one-tap buttons, and `run_until`
  loops and stops on signal. **Exactly-once delivery under concurrency** is already
  proven in Phase 4 (`SKIP LOCKED` integration test — no row is double-claimed).
- **Real run** (`logs/phase-7/run.log`): a refund request was **held by the gate**
  (`MessageReceived` → `ApprovalRequested`, no refund executed, customer told it's
  flagged), and the worker delivered a due reminder with Confirm/Reschedule.

## On ADR-0005 (airlock)

The gate realizes the **airlock discipline** — a model can't take a money-moving
action on its own; it's gated by the architecture. It's modeled behind the
`ApprovalGate` port (the boundary is ours), with the in-memory adapter for tests.
The production adapter — a dashboard-driven pending-approval flow — is wired in the
composition root alongside the dashboard (Phase 8); the published `airlock-hitl`
package targets a self-contained agent loop, so Frontdesk implements the same
discipline natively against its own port rather than importing that loop.

## Definition of Done

- [x] The worker process drives `SendDueReminders` on an interval; reminders
      scheduled on booking, cancelled on cancel/move (Phase 3), exactly-once under
      concurrency (Phase 4).
- [x] A gated action pauses and only runs after approval — covered by tests and a
      real run.
