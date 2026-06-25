# Phase 1 — Domain core — report

**Status:** Done (2026-06-25)

## What was built (`src/frontdesk/domain/`, pure, stdlib only)

- `ids.py` — opaque `NewType` ids per entity.
- `enums.py` — `Channel`, `AppointmentStatus`, `ReminderStatus`, `RiskTier`, `MessageRole`.
- `money.py` — `Money` (integer minor units + ISO-4217 currency), validated.
- `errors.py` — the domain error hierarchy (`SlotUnavailable`, `DoubleBooking`,
  `LeadTimeViolation`, `InvalidTransition`, …).
- `models.py` — value objects and entities (`TimeSlot` with half-open overlap +
  duration, `WorkingHours`, `KnowledgeItem`, `Service`, `Resource`, `Business`,
  `Customer`, `Message`, `Appointment`, `Reminder`), all frozen and validated.
- `availability.py` — `free_slots(...)` (timezone-aware, respects working hours,
  the per-business buffer, and lead time) and `ensure_bookable(...)`.
- `transitions.py` — the appointment and reminder state machines as pure functions
  that raise `InvalidTransition` on a disallowed move.

## Verification

- **The gate** (`make check`, logged to `logs/phase-1/check.log`): ruff clean,
  import-linter **3/3 kept** (domain imports nothing outward), mypy `--strict`
  green, pytest **48 passed, 100 % coverage** (branch). Every state transition —
  valid and rejected — and every validation branch is tested.
- **Real run** (`logs/phase-1/domain-run.log`): a realistic scenario — Ana's
  Studio (Montevideo, UTC−3, 60-min lead, 15-min buffer), a busy 12:00–13:00 local
  slot — produced exactly the right free slots (11:00 local, then 13:15/13:30/13:45
  after the buffered busy block), validated the chosen slot, and ran the
  `pending → confirmed → completed` lifecycle. Output matched expectations.

## Notes

- The domain is stdlib-only (no pydantic, no I/O) so it stays trivially testable;
  pydantic is reserved for the edges.
- Minor branch initially missed (a valid `Service` was never constructed) — closed
  with a test; coverage is 100 %.

## Definition of Done

- [x] Entities, value objects, enums, ids, and errors per the contracts.
- [x] Availability math, booking validation, and both state machines, pure.
- [x] Unit tests cover the rules and every transition (incl. rejected) — 100 %.
- [x] The package imports nothing from the stack; import-linter green.
