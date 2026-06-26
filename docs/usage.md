# Using Frontdesk

This is the practical guide: what Frontdesk does, how it works, and how to run,
use, configure, and extend it. For the product framing see the
[README](../README.md); for the engineering rationale see the
[architecture overview](architecture/overview.md) and the [ADRs](adr/).

---

## What problem it solves

Small, appointment-based businesses — salons, clinics, tutors, studios — run on
WhatsApp and Telegram, and lose money two ways:

- **Missed messages.** An enquiry arrives after hours or while staff are busy, goes
  unanswered, and the customer books with whoever replied first.
- **No-shows.** Forgotten appointments leave empty slots that can't be re-sold.

Frontdesk is an AI front desk that lives on those channels and actually gets work
done: it answers questions, **books into a real calendar** (without double-booking),
**reminds** customers to kill no-shows, and **escalates** anything it shouldn't
decide alone. Money-moving actions (a refund) are **held for human approval**.

## How it works

```
customer message ─▶ channel webhook ─▶ the Assistant (LLM tool-use loop)
                                          │   tools = the use cases:
                                          │   answer · find_availability · book
                                          │   reschedule · cancel · escalate · issue_refund
                                          ▼
                         the typed domain core decides whether & how
                         (working hours, lead time, buffer, no double-book)
                                          │
                         Postgres ◀───────┘   appointment + reminders persisted
                                          │
                         reply ──▶ back to the customer's channel
```

The model decides *what* to attempt; the **typed, tested core decides whether and
how** it actually happens. It answers only from the business's knowledge base and
its real service list and calendar — it never invents times, prices, or services.
A background **worker** polls Postgres for due reminders and sends them with
one-tap Confirm/Reschedule. Sensitive tools pass an **approval gate**
([airlock](https://github.com/fedorello/airlock)) and wait for a human.

The design is hexagonal (ports & adapters): the domain knows nothing about
WhatsApp, Postgres, or any LLM vendor — each is an adapter behind a port. See
[`architecture/overview.md`](architecture/overview.md).

---

## Prerequisites

- **Docker** (for Postgres, Redis, and the one-command stack)
- **[uv](https://docs.astral.sh/uv/)** (Python 3.14 backend)
- **pnpm** + **Node 24** (Next.js dashboard)
- An **LLM API key** — any OpenAI-compatible or Anthropic endpoint. The demo
  defaults to `deepseek/deepseek-v4-flash` via [OpenRouter](https://openrouter.ai).

Everything is driven through the `Makefile`; run `make help` to list targets.

## Quick start — the whole product in Docker

```bash
git clone https://github.com/fedorello/frontdesk && cd frontdesk

cp deploy/docker/.env.example deploy/docker/.env
# edit deploy/docker/.env and set FRONTDESK_LLM_API_KEY=sk-or-...

make stack-up        # builds + runs: migrate → seed → api + worker + dashboard
```

This starts the full stack:

| Service | What | URL |
| --- | --- | --- |
| `dashboard` | the admin UI | http://localhost:3000 |
| `api` | webhooks + chat + approvals | http://localhost:8000 |
| `worker` | sends due reminders | — |
| `postgres` / `redis` | data + events | :5432 / :6379 |

`migrate` runs the Alembic migration (schema + the no-double-book constraint) and
`seed` inserts a demo business (**Ana Studio**, one service: Haircut). Tail logs
with `make stack-logs`; stop and wipe with `make stack-down`.

> The demo freezes time (`FRONTDESK_FIXED_NOW`) so offered slots stay bookable
> while you click around. Unset it for a real, moving clock.

## Try it

Open **http://localhost:3000/chat** and talk to the agent like a customer:

- *"What services do you have?"* → it answers from the real service list only.
- *"When's the earliest haircut?"* → it calls `find_availability` and offers real slots.
- *"Book the 09:30 one."* → it books a real appointment, persisted in Postgres.
- *"I'd like a refund for ap-1."* → **held for approval**, not executed.

Under each reply, expand **🧠 Agent reasoning** to see the agent's thoughts and the
exact tool calls (`find_availability(service: "Haircut") → …`).

Open **http://localhost:3000/approvals** — the refund is waiting there (raised by
the airlock gate). Approve or reject it. You can verify it landed in Postgres:

```bash
docker compose -f deploy/docker/docker-compose.yml \
  exec -T postgres psql -U frontdesk -d frontdesk -c "SELECT starts_at, status FROM appointment;"
```

## A one-shot scripted demo

Without the dashboard, `make demo` seeds a business and drives a booking end to end
(a WhatsApp-style message → the real assistant → a persisted appointment):

```bash
make up                                  # just Postgres + Redis
FD_LLM_KEY=sk-or-... make demo
```

---

## Development (without Docker images)

Run the backend and dashboard directly for fast iteration:

```bash
# Backend
make install            # uv sync
make up                 # Postgres + Redis
make check              # the full gate: ruff, mypy --strict, import-linter, pytest
make serve              # uvicorn with reload on :8000 (needs FRONTDESK_* env)

# Dashboard
make dashboard-install
make dashboard-check    # typecheck, lint, format, test, build
make dashboard-dev      # http://localhost:3000
```

The backend reads configuration from `FRONTDESK_*` environment variables (or an
`apps/api/.env` file). At minimum set `FRONTDESK_LLM_API_KEY`.

## Configuration

Every setting is a `FRONTDESK_*` environment variable with a sensible default. The
full reference — LLM provider, channels, the demo clock, CORS — is in
[`configuration.md`](configuration.md).

## Connecting real WhatsApp / Telegram

The inbound path (webhook signature, idempotency, parsing) is real out of the box;
**outbound replies** need real provider credentials. Set the channel variables in
your `.env` (see [configuration.md](configuration.md)) and point the provider's
webhook at:

- WhatsApp Cloud API → `POST https://your-host/webhooks/whatsapp`
  (verify token + `X-Hub-Signature-256` app-secret).
- Telegram Bot API → `POST https://your-host/webhooks/telegram`
  (secret-token header).

Without tokens, the stack still runs end to end locally — outbound replies are
logged instead of sent. Full request/response shapes are in [`api.md`](api.md).

## The HTTP API

- `POST /api/chat` — the synchronous web-chat the dashboard uses.
- `GET /api/approvals` · `POST /api/approvals/{id}` — the approvals inbox.
- `GET|POST /webhooks/whatsapp`, `POST /webhooks/telegram` — the channels.

Request/response examples: [`api.md`](api.md).

## The reminder worker

`make stack-up` runs it as a separate process. It polls Postgres
(`FOR UPDATE SKIP LOCKED`, so two workers never double-send) and delivers each due
reminder once. Reminders are scheduled when an appointment is booked (24h and 2h
before) and cancelled when it's cancelled or moved. Run it standalone with
`python -m frontdesk.interface.run_worker`.

---

## Extending it

- **Add a service or change hours/knowledge.** Insert into the `service`,
  `resource`, and `business` tables (see `apps/api/scripts/seed.py`). The assistant
  picks them up automatically and will only ever offer real services.
- **Swap the model.** Config only — set `FRONTDESK_LLM_PROVIDER`,
  `FRONTDESK_LLM_MODEL`, `FRONTDESK_LLM_BASE_URL`. Any OpenAI-compatible or
  Anthropic endpoint works (see [ADR-0006](adr/0006-model-agnostic-llm-provider.md)).
- **Add a channel.** Implement the `MessagingPort` (outbound) + a webhook parser,
  like `infrastructure/channels/whatsapp.py`. The core never changes
  ([ADR-0002](adr/0002-channels-behind-a-messaging-port.md)).
- **Gate another action.** Tag a new tool sensitive and route it through the
  `ApprovalGate`; it'll appear in the approvals inbox
  ([ADR-0005](adr/0005-human-in-the-loop-via-airlock.md)).

## Testing & quality gates

| Command | What it checks |
| --- | --- |
| `make check` | ruff format + lint, import-linter contracts, mypy `--strict`, pytest + coverage |
| `make test-integration` | the SQL adapters against a real Postgres (needs `make up`) |
| `make dashboard-check` | dashboard typecheck, lint, format, vitest, build |
| `make dashboard-e2e` | Playwright end-to-end |

The same commands run in CI (`.github/workflows/ci.yml`) on every push.

## Troubleshooting

- **"Can't reach the API on :8000"** in the dashboard → the api container isn't up;
  run `make stack-up` (or `make serve` for dev).
- **The agent doesn't call a tool / replies oddly** → it likely needs a larger
  `FRONTDESK_LLM_MAX_TOKENS` (reasoning models spend tokens thinking before the tool
  call), or a more capable model.
- **A booking fails with "that time just passed"** → on a real clock, a slot can
  expire between being offered and booked; the agent re-reads availability and
  offers fresh slots. Freeze the clock (`FRONTDESK_FIXED_NOW`) for a stable demo.
- **`docker compose` grabs the wrong containers** → the project is named `frontdesk`
  to avoid collisions; always go through the `Makefile` targets.
