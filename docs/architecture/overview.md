# Architecture overview

How Frontdesk is put together: the hexagon, the domain model, the ports and
adapters, and the three flows that matter — answering a message, booking an
appointment, and reminding a customer.

The guiding rule is [`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md):
correctness first, everything testable in isolation, SOLID with dependency
injection, and a domain core that imports no framework, no database, no HTTP, and
no LLM.

## The shape

One repository, two deployables, shared infrastructure:

```
                       ┌─────────────────────────────┐
   WhatsApp ──webhook─▶│                             │
   Telegram ──webhook─▶│   apps/api  (FastAPI)        │──┐
                       │   • channel webhooks        │  │   ┌────────────┐
   Owner's browser ───▶│   • dashboard API           │◀─┼──▶│ PostgreSQL │  durable state
                       │                             │  │   └────────────┘
                       │   apps/api worker           │  │   ┌────────────┐
   (every ~minute) ───▶│   • due-reminder loop       │──┘──▶│   Redis    │  events / pub-sub
                       └─────────────────────────────┘      └────────────┘
                                     ▲
   Owner's browser ──────────────────┘  apps/dashboard (Next.js admin)
```

- **`apps/api`** runs two process types from one codebase: a **web** process
  (channel webhooks + the dashboard's JSON API) and a **worker** process (the
  due-reminder loop, and any deferred sends).
- **`apps/dashboard`** is the business owner's admin app — calendar,
  conversations, settings, and a clear log of what the assistant did and what it
  escalated.
- **PostgreSQL** holds all durable state. **Redis** carries ephemeral events
  (live dashboard updates, the approval gate) — never the source of truth.

## The hexagon

`apps/api` is layered so dependencies point **inward**. import-linter enforces
this in CI.

```
interface  ──▶  application  ──▶  domain  ◀──  application  ◀──  infrastructure
(driving)                         (pure)                          (driven)
```

- **`domain/`** — entities, value objects, and pure business rules. Availability
  math, booking rules, reminder policy, the assistant's intent model. No I/O, no
  imports of any library in the stack.
- **`application/`** — use cases and the **ports** (Python `Protocol`s) the core
  depends on. Orchestrates the domain; knows nothing about the concrete database,
  channel, or model.
- **`infrastructure/`** — the **adapters**: SQLAlchemy repositories, the WhatsApp
  and Telegram clients, the LLM providers, the Redis event bus, the clock and id
  generators — and an in-memory fake for every port.
- **`interface/`** — the driving adapters: FastAPI routers (webhooks + dashboard
  API) and the worker entry point. Thin; they translate the outside world into
  use-case calls.

## Domain model

The nouns, kept small and explicit (each business is a tenant — see
[multi-tenancy](#multi-tenancy)):

- **Business** — the tenant: name, timezone, working hours, channels, and a
  knowledge base (FAQ snippets) the assistant answers from.
- **Service** — something bookable: name, duration, price, and which resources
  can perform it (e.g. "Haircut, 45 min, with any barber").
- **Resource** — a person or asset the booking consumes (a stylist, a room, a
  chair). Availability is per-resource.
- **Customer** — a person, identified per channel (a phone number on WhatsApp, a
  chat id on Telegram), with a name and language once known.
- **Conversation** / **Message** — the running thread with a customer on a
  channel; the assistant's working memory.
- **Appointment** — a booked `Service` for a `Customer` on a `Resource` in a time
  range, with a lifecycle: `pending → confirmed → completed | cancelled | no_show`.
- **TimeSlot / Availability** — derived, never stored as truth: free ranges
  computed from a resource's working hours minus existing appointments minus
  lead-time and buffers.
- **Reminder** — a scheduled message about an appointment, with a `due_at` and a
  status (`pending → sent | cancelled`). Durable (see
  [the reminder flow](#flow-3-the-reminder)).

## Ports (what the core depends on)

The application layer defines these; adapters implement them; tests use in-memory
fakes. Adding a channel, a model, or a calendar backend means adding an adapter —
never touching the core ([ADR-0001](../adr/0001-architecture-foundations.md)).

| Port                  | Responsibility                                                            |
| --------------------- | ------------------------------------------------------------------------- |
| `MessagingPort`       | Send a message (text + quick-reply buttons) to a customer on any channel.  |
| `LlmProvider`         | One normalized chat/tool-use call to any model.                           |
| `Calendar`            | Read availability and create/move/cancel appointments.                     |
| `*Repository`         | Persist and load businesses, customers, conversations, appointments, reminders. |
| `ReminderStore`       | Enqueue a reminder at `due_at`; claim and mark due ones (durable).         |
| `EventPublisher`      | Emit events (new message, escalation, booking) for the live dashboard.     |
| `ApprovalGate`        | Pause a sensitive action for human approval (backed by `airlock-hitl`).    |
| `Clock` / `IdGenerator` | Injected time and ids — deterministic tests, UTC everywhere.             |

## The assistant

The assistant is a **tool-use (ReAct) loop**, not a free-text chatbot. Its tools
are the domain use cases — so the model decides *what* to do, and the typed,
tested core decides *whether and how* it actually happens
([ADR-0007](../adr/0007-assistant-as-tool-use-agent.md)):

- `answer_question(topic)` — reply from the business's knowledge base (no
  inventing facts; if it doesn't know, it says so or escalates).
- `find_availability(service, around)` — the real free slots.
- `book(service, slot, customer)` — create an appointment (the core enforces no
  double-booking, lead time, and policy).
- `reschedule(appointment, slot)` / `cancel(appointment)`.
- `escalate(reason)` — hand off to a human.

Safe tools (answer, find availability) run on their own. Anything that moves money
or is hard to undo passes the **approval gate** before it happens — the same
discipline as [Airlock](https://github.com/fedorello/airlock), reused via the
`airlock-hitl` package ([ADR-0005](../adr/0005-human-in-the-loop-via-airlock.md)).

## Three flows

### Flow 1: the answer

1. A customer messages on WhatsApp → Meta calls our **webhook** (`interface`).
2. The router verifies the signature, normalizes the payload through the WhatsApp
   **adapter**, and calls `HandleInboundMessage` (`application`).
3. The use case loads the conversation, runs the **assistant loop** with the
   business's tools and knowledge base, and produces a reply (plus any actions).
4. The reply goes out through the `MessagingPort` adapter; the exchange is
   persisted; an event is published for the live dashboard.

### Flow 2: the booking

1. Inside the loop the model calls `find_availability`, then `book`.
2. The `Calendar` adapter computes real free slots from the resource's hours minus
   existing appointments, and creates the `Appointment` in a single transaction
   that **rejects double-booking** (DB constraint + application check).
3. On success, the use case **schedules the reminders** for that appointment
   (e.g. 24h and 2h before) via the `ReminderStore`, and confirms to the customer.

### Flow 3: the reminder

Durable and restart-safe, with no external queue
([ADR-0004](../adr/0004-durable-reminders-in-postgres.md)):

1. A reminder is a row in PostgreSQL with `due_at` and `status = pending`.
2. The **worker** loop wakes every minute and claims due reminders with
   `SELECT … WHERE due_at <= now() AND status = 'pending' FOR UPDATE SKIP LOCKED`
   — so multiple workers never send the same reminder twice.
3. It sends the reminder (with one-tap **confirm** / **reschedule** buttons) via
   the `MessagingPort` and marks it `sent`.
4. The customer's tap returns as an inbound message (Flow 1) and updates the
   appointment — a forgotten slot becomes a kept one, or a freed one to resell.

## Multi-tenancy

Every row that belongs to a business carries its `business_id`; every repository
query is scoped to the current tenant, resolved from the inbound channel
(which WhatsApp number / Telegram bot received the message) or the authenticated
dashboard session. One deployment serves many businesses
([ADR-0003](../adr/0003-multi-tenant-by-business.md)).

## Package structure

```
apps/api/
  src/frontdesk/
    domain/          # entities, value objects, pure rules. No I/O.
    application/     # use cases + ports (Protocols)
    infrastructure/  # adapters: db, channels, llm, redis, fakes
    interface/       # FastAPI routers (webhooks + dashboard API), worker
    core/            # Settings (pydantic-settings), composition root
  alembic/           # migrations
  tests/             # unit (fakes) + integration (real Postgres/Redis)
apps/dashboard/      # Next.js admin app
deploy/              # Docker Compose, Dockerfiles
docs/
```

## Deployment topology

`docker compose up` brings up: **postgres**, **redis**, the api **web** process,
the api **worker** process, and the **dashboard**. The same images run in
production. A `Makefile` is the single entry point (`make up`, `make test`,
`make check`). CI runs the full gate on every push.

## Security & privacy

- **Webhook verification.** Every channel webhook verifies its signature/secret
  before doing any work.
- **Secrets** stay in env / a secrets store, never in git — one typed `Settings`
  object reads them.
- **Tenant isolation.** No query crosses a `business_id` boundary.
- **Data minimization.** We store what's needed to run bookings and conversations;
  PII is never sent to logs, and the assistant is grounded — it answers from the
  business's knowledge base rather than inventing facts.
- **Human-in-the-loop.** Irreversible or money-moving actions require approval, so
  a model mistake can't quietly cost the business money.
