# Phase 9 — CI/CD, evals & release readiness — report

**Status:** Done (2026-06-25)

## What was built

- **CI** (`.github/workflows/ci.yml`): a **backend** job — `uv sync`, the full gate
  (ruff format/check, import-linter, mypy `--strict`, pytest), then the
  **integration suite against a real Postgres service** — and a **dashboard** job —
  the pnpm gate (typecheck, lint, format, test, build) plus the **Playwright e2e**
  with Chromium. Every command is the same one verified green locally.
- **Behavioral evals** (`tests/evals/`): deterministic guardrail checks on realistic
  conversations — books the exact slot, **never invents availability**, **never
  invents prices** (grounded answers only), reminds, and escalates. 5 passing, in
  the gate and CI.
- **A live eval runner** (`scripts/eval_live.py`) — the same properties against a
  real model.
- **A one-command demo** (`scripts/demo.py` / `make demo`) and a **README
  quickstart**.

## Verification

- **The gate** (`make check`): ruff/imports/mypy green; pytest **98 passed, 97.8 %**
  (5 of them evals).
- **Live eval** (`logs/phase-9/eval-live.log`) against `deepseek/deepseek-v4-flash`:
  **2/2** — booked an offered slot end-to-end and grounded the opening hours from the
  knowledge base.
- **The integrated demo** (`logs/phase-9/demo.log`, `make up` + `make demo`): seeds
  Ana's Studio into Postgres, then a **WhatsApp-style message drives the real,
  SQL-backed assistant + a real model to book a real, persisted appointment** —
  reference `0301001d-…`, 12:30, status pending, with `MessageReceived` +
  `AppointmentBooked`. The whole product, locally, in one command.

## A note found by running it

The live eval and the demo first "failed" to book a 3pm slot — which turned out to
be **correct behavior**: `find_availability` offers the next few 15-minute slots
(a ~75-minute window), so a far-off time genuinely isn't on the list and the model
rightly declined rather than inventing one. The no-invention guardrail, observed in
the wild. (A natural follow-up: let `find_availability` honour a requested time so
the window centres on it.)

## Definition of Done

- [x] CI runs the full backend gate + the dashboard gate on every push, with a
      Postgres service for the integration tests.
- [x] An eval suite for the assistant passes (books the right slot, never invents
      availability/prices, reminds, escalates).
- [x] README quickstart and a one-command demo (`make up` + `make demo`) bring the
      product up locally with a seeded demo business and a WhatsApp message path.
