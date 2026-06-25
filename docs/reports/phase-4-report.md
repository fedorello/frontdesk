# Phase 4 — Persistence (PostgreSQL) — report

**Status:** Done (2026-06-25)

## What was built

- `infrastructure/db.py` — the async SQLAlchemy engine + session factory.
- `infrastructure/postgres/schema.py` — the schema as ordered DDL statements (one
  source of truth), including `CREATE EXTENSION btree_gist` and the
  **`no_double_book` gist `EXCLUDE` constraint**.
- `infrastructure/postgres/adapters.py` — the real adapters for every persistence
  port: `SqlBusinessRepository`, `SqlServiceRepository`, `SqlCustomerRepository`,
  `SqlConversationRepository`, `SqlAppointmentRepository`, `SqlReminderStore`
  (claim with `FOR UPDATE SKIP LOCKED`), and `SqlCalendar` (availability + bookings,
  mapping the DB constraint violation to `DoubleBooking`).
- `alembic/` — async env + the initial migration, which runs the same DDL
  statements as the tests (so they can't drift). `make test-integration` added.

## Verification

- **Unit gate** (`make check`): ruff clean, import-linter 3/3, mypy `--strict`
  green over 41 files, pytest **75 passed, 97.2 %** (the DB adapters are omitted
  from the unit-coverage gate — they're covered by the integration suite).
- **Integration suite on a real Postgres** (`logs/phase-4/integration.log`,
  `make up` + `make test-integration`): **9 passed**. The SQL adapters pass the
  *same* port-contract suite as the fakes, **plus** DB-level proofs: an overlapping
  insert is rejected by the gist `EXCLUDE` constraint (`IntegrityError`); the
  calendar maps that to `DoubleBooking`; and `claim_due` skips rows already locked
  by a concurrent transaction (`SKIP LOCKED`).
- **Migration verified**: `alembic upgrade head` creates the schema and the
  `no_double_book` constraint; `downgrade base` and a re-`upgrade` both work.

## Problems found and fixed (by running it)

- `Money` had to be imported from `frontdesk.domain.money` (mypy strict forbids the
  implicit re-export through `models`).
- asyncpg raised `AmbiguousParameterError` on a `:ignore IS NULL` NULL parameter —
  fixed by building the optional clause conditionally instead of binding `NULL`.

## Definition of Done

- [x] SQLAlchemy models/queries + Alembic migration (btree_gist + exclusion constraint + reminder index).
- [x] Adapters pass the same port-contract suite as the fakes.
- [x] Integration tests on real Postgres: double-book rejected, `SKIP LOCKED` no double-claim, tenant scoping.
