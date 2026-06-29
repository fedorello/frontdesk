# Frontdesk

**An open-source AI front desk for small service businesses — it answers, books,
and reminds, so you stop losing money to missed messages and no-shows.**

Salons, clinics, tutors, studios, barbershops, repair shops — they run on
WhatsApp and Telegram. A message arrives after hours and nobody replies, so the
booking goes to whoever answered faster. A client forgets the appointment, the
slot sits empty, and it's too late to resell it. Staff burn hours on the same
back-and-forth: "what are your prices?", "do you have Friday at 5?", "can we move
it to Tuesday?".

Frontdesk is the assistant that handles all of that on the channels your
customers already use.

---

## The problem

For an appointment-based business, two leaks quietly drain revenue:

- **Missed messages.** Most enquiries arrive outside working hours or while staff
  are with a client. An unanswered message is a lost booking — the customer moves
  on to the next result.
- **No-shows.** Forgotten appointments leave empty slots that can't be filled at
  the last minute. For many small businesses that's 20–40% of the calendar.

The usual "fixes" don't fit a small business: a full-time receptionist is
expensive, generic chatbots are frustrating and can't actually book anything, and
booking widgets don't help the customer who only ever messages you on WhatsApp.

## What Frontdesk does

An AI assistant that lives on the channels your customers use and actually gets
work done:

- **Answers the common questions** — hours, prices, services, location,
  "do you do X?" — instantly, 24/7, in the customer's language.
- **Books appointments into a real calendar** — checks availability, avoids
  double-booking, and confirms.
- **Kills no-shows** — sends smart reminders with one-tap confirm or reschedule,
  so a forgotten slot becomes a kept one (or a freed one you can resell).
- **Hands off to a human** — anything it shouldn't decide alone (a refund, an
  edge case, an unhappy customer) is escalated, not guessed.

Self-hostable, multilingual, and model-agnostic: you own your data, your
calendar, and your customer relationships.

The point in one line: **turn missed messages and forgotten appointments into
booked, kept revenue — without hiring a receptionist.**

## Who it's for

Any small, appointment-based service business: hair & beauty, clinics and
therapists, tutors and coaches, studios, barbershops, repair and trades. If your
calendar is your revenue and your inbox is WhatsApp, this is for you.

## Architecture

Frontdesk is built as a real, maintainable product, not a demo script:

- **Hexagonal architecture (ports & adapters).** The domain core — bookings,
  availability, reminders, the assistant's decision loop — knows nothing about
  WhatsApp, a database, or any LLM vendor. Everything external is an adapter
  behind a port.
- **Channel-agnostic.** WhatsApp and Telegram are adapters behind one messaging
  port; adding a channel never touches the core.
- **Model-agnostic.** Every LLM provider sits behind one port — swap models with
  a config change.
- **Human-in-the-loop where it matters.** Sensitive actions pass an approval gate
  before they happen (the same discipline as
  [Airlock](https://github.com/fedorello/airlock)).
- **An admin dashboard** for the business: calendar, conversations, settings, and
  a clear view of what the assistant did and what it escalated.

The stack and pinned versions live in [`docs/stack.md`](./docs/stack.md): a Python
3.14 / FastAPI core, a Next.js 16 admin app, Postgres for data (with a gist
exclusion constraint that makes double-booking impossible), and Redis for events —
run locally and in production through Docker Compose, with a Makefile as the single
entry point.

## Quickstart

Prerequisites: Docker, [`uv`](https://docs.astral.sh/uv/), `pnpm`, and Node 24.

```bash
make install          # backend deps
make check            # the full gate: ruff, mypy, import-linter, pytest

make up               # Postgres + Redis
make test-integration # adapters against a real Postgres (double-book rejected, SKIP LOCKED)

# The integrated demo: seeds a business, then a WhatsApp-style message drives the
# real assistant (SQL-backed) to book a real, persisted appointment via a real model.
FD_LLM_KEY=sk-or-... make demo

# The admin dashboard (calendar, conversations, settings, approvals inbox)
make dashboard-install
make dashboard-check  # typecheck, lint, test, build
make dashboard-dev    # http://localhost:3000
```

Or run the **whole product in Docker** — Postgres, Redis, the migration, the API,
the reminder worker, and the dashboard, in one command:

```bash
cp deploy/docker/.env.example deploy/docker/.env   # add your LLM key
make stack-up      # migrate → api (:8000) + worker + dashboard (:3000)
make stack-logs
make stack-down    # stop and wipe the volume
```

The LLM is model-agnostic — any OpenAI-compatible or Anthropic endpoint; the demo
defaults to `deepseek/deepseek-v4-flash` via OpenRouter.

## Platform admin

Beyond the per-business owner dashboard, platform operators get a **cross-tenant
analytics dashboard** at `/admin`: signups over time, agent activity, bookings with
no-show / cancellation rates, an activation funnel, and a searchable per-business
directory. It is **read-only and aggregate-only** — counts and configuration, never a
customer's messages, phone number, or intake answers
([ADR-0012](./docs/adr/0012-admin-role-and-cross-tenant-analytics.md),
[design](./docs/design/admin-dashboard.md)).

### Granting the admin role

`admin` is a separate account role, provisioned **out-of-band** — never self-granted and
never from the request path:

1. Make sure the account already exists (it has signed up).
2. List the emails to grant (comma-separated) in the API's environment:
   `FRONTDESK_ADMIN_EMAILS=ops@example.com,you@example.com`.
3. Run the idempotent promotion (with the database up):

   ```bash
   make promote-admin
   ```

It sets `role=admin` on the listed accounts and is safe to re-run. The role lives in the
database; the request path checks only the stored role. Sign in again (or reload) and the
**Admin** link appears in the nav.

## Documentation

- **[Usage guide](./docs/usage.md)** — what it does, how it works, and how to run,
  try, configure, and extend it. Start here.
- **[Configuration](./docs/configuration.md)** — every `FRONTDESK_*` setting.
- **[HTTP API](./docs/api.md)** — web chat, approvals inbox, channel webhooks.
- **[Architecture](./docs/architecture/overview.md)** · **[ADRs](./docs/adr/)** ·
  **[full docs index](./docs/README.md)**.

## Status

Built in the open, in staged and reviewed phases (see
[`docs/plans/implementation-plan.md`](./docs/plans/implementation-plan.md) and the
per-phase reports in [`docs/reports/`](./docs/reports)). The core product works
end-to-end: a real WhatsApp message books a real appointment, with reminders and an
approval gate for sensitive actions.

## How it's built

Directing Claude Code against a staged spec — the product framing, the
architecture, and the review are mine. The interesting part of the diff history
isn't the code, it's what an AI-native delivery loop looks like when the
engineer's job is to specify, review, and decide.

Everything is built and reviewed against [`CODING_PRINCIPLES.md`](./CODING_PRINCIPLES.md).

## License

[MIT](./LICENSE)
