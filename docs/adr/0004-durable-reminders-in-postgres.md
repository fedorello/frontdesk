# ADR-0004: Durable reminders in PostgreSQL

**Status:** Accepted

## Context

Cutting no-shows is the headline value, and it depends entirely on reminders firing
**reliably** — hours or a day after a booking, surviving restarts and deploys, and
never sent twice. A reminder is durable, time-based state tied to an appointment. We
need a scheduler we can trust without adding fragile moving parts to a small,
self-hostable deployment. External async queues were considered: `arq` is in
maintenance-only mode, and Celery is heavy for this.

## Decision

Store reminders **in PostgreSQL** and drive them with a small **polling worker** — no
external queue:

- A reminder is a row with `due_at` and `status` (`pending → sent | cancelled`),
  created in the same transaction as the appointment.
- A worker wakes about once a minute and claims due rows with
  `SELECT … WHERE due_at <= now() AND status = 'pending' FOR UPDATE SKIP LOCKED`,
  sends them, and marks them `sent`.
- `SKIP LOCKED` makes it safe to run multiple workers — no reminder is ever sent
  twice. Cancelling an appointment cancels its pending reminders in the same
  transaction.

Redis stays for **ephemeral** events (live dashboard, the approval gate), not for
durable scheduling.

## Consequences

- Reminders are transactional with bookings and survive any restart — the reliability
  the feature lives or dies by.
- One fewer infrastructure dependency to operate; the polling worker is trivial to
  reason about and test.
- Minute-granularity scheduling, which is more than enough for appointment reminders.
  Sub-second scheduling is explicitly out of scope.
