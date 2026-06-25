# Phase 3 — Use cases & the assistant loop — report

**Status:** Done (2026-06-25)

## What was built (`application/`)

- `appointments.py` — `BookAppointment`, `RescheduleAppointment`, `CancelAppointment`,
  and a `ReminderScheduler` that schedules the 24h/2h reminders (skipping any whose
  time is already past) and refreshes them on reschedule.
- `worker.py` — `SendDueReminders`: claim due reminders, send each with
  Confirm/Reschedule buttons, mark sent.
- `assistant.py` — the **tool-use loop**. The model's tools *are* the use cases
  (`answer_question`, `find_availability`, `book`, `reschedule`, `cancel`,
  `escalate`); a handler-map dispatches them. The typed core decides what actually
  happens — the model only handles language and intent. Resolves the tenant from
  the inbound number, persists the conversation, publishes events, and replies.

## Verification

- **The gate** (`logs/phase-3/check.log`): ruff clean, import-linter **3/3 kept**
  (application still imports only the domain), mypy `--strict` green over 34 files,
  pytest **75 passed, 97.2 % coverage**.
- **Flows tested against a scripted fake LLM** (deterministic, no live calls): the
  answer flow relays only knowledge-base facts; the booking flow books a real slot
  and schedules reminders; escalation publishes the event and hands off;
  reschedule+cancel run through the loop; **grounding** (no invented answers) and
  the **max-steps fallback** and **unknown-number** guard are covered; the worker
  delivers due reminders.
- **Real run** (`logs/phase-3/assistant-run.log`): "Hi, can I get a haircut this
  afternoon?" → the assistant called `find_availability` then `book`, booked
  16:00 UTC (13:00 Montevideo), published `MessageReceived` + `AppointmentBooked`,
  scheduled only the future 2h reminder (the 24h one correctly skipped), and the
  worker later delivered it with the one-tap buttons. Output matched expectations.

## Definition of Done

- [x] `BookAppointment`, `RescheduleAppointment`, `CancelAppointment`, `SendDueReminders`.
- [x] The assistant loop against a scripted fake provider, deterministic.
- [x] The three flows pass end-to-end against fakes; grounding + escalation tested;
      no live calls.
