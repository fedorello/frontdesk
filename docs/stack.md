# Technology stack

The stack and pinned versions for Frontdesk. Versions are the current stable
releases, verified 2026-06-25. Pin exact versions in the manifests; this file is
the human-readable rationale.

Two deployables, one repo:

- **`apps/api`** — the Python core + web/worker processes (the product).
- **`apps/dashboard`** — the Next.js admin app for the business owner.

Plus shared infrastructure (PostgreSQL, Redis) wired together with Docker Compose.

## Backend — `apps/api` (Python)

| Package             | Version  | Why                                                                                   |
| ------------------- | -------- | ------------------------------------------------------------------------------------- |
| Python              | 3.14.x   | Current stable feature line; 3.13 is maintenance-only.                                 |
| FastAPI             | 0.138.x  | Async web framework for the channel webhooks and the dashboard API. Typed, fast.      |
| Uvicorn             | 0.49.x   | ASGI server.                                                                          |
| Pydantic            | 2.13.x   | Domain DTOs, settings, and request/response validation. (v3 not out.)                 |
| pydantic-settings   | 2.14.x   | Typed configuration from env — one `Settings` object, no scattered `os.environ`.      |
| SQLAlchemy          | 2.0.x    | Async ORM/core for PostgreSQL. (2.1 is still pre-release — stay on 2.0.x.)             |
| Alembic             | 1.18.x   | Database migrations, versioned in the repo.                                            |
| asyncpg             | 0.31.x   | Async PostgreSQL driver.                                                              |
| httpx               | 0.28.x   | The HTTP client for every outbound call (LLM, WhatsApp, Telegram) — injected, mockable. |
| redis (redis-py)    | 8.0.x    | Redis client for the event bus / pub-sub.                                             |
| airlock-hitl        | ^0.1     | The human-in-the-loop approval gate for sensitive actions (our own package — dogfooded). |

We deliberately do **not** take an external task-queue dependency for reminders.
A scheduled reminder is durable, time-based state tied to a booking, so it lives
in PostgreSQL and is driven by a small polling worker (see
[ADR-0004](./adr/0004-durable-reminders-in-postgres.md)). `arq` was considered and
rejected (it is in maintenance-only mode).

## Tooling — `apps/api`

| Tool            | Version | Role                                                            |
| --------------- | ------- | -------------------------------------------------------------- |
| uv              | 0.11.x  | Package and environment manager.                               |
| pytest          | 9.1.x   | Test runner.                                                   |
| pytest-asyncio  | 1.x     | Async test support.                                            |
| ruff            | 0.15.x  | Lint + format (single tool).                                   |
| mypy            | 2.x     | Strict static typing (`mypy --strict`).                        |
| import-linter   | 2.12    | Enforces the hexagonal import boundaries in CI.                |

## Dashboard — `apps/dashboard` (TypeScript)

| Package      | Version | Why                                                                          |
| ------------ | ------- | ---------------------------------------------------------------------------- |
| Node.js      | 24.x    | Current active LTS.                                                          |
| Next.js      | 16.2.x  | App Router admin app (calendar, conversations, settings).                    |
| React        | 19.2.x  | UI runtime.                                                                  |
| TypeScript   | 5.9.x   | Pinned to Next 16's validated toolchain to keep the build warning-free — **not** bleeding-edge TS 6. |
| Tailwind CSS | 4.3.x   | Styling.                                                                     |

Test/lint tooling mirrors the validated Next 16 toolchain (Vitest, ESLint,
Prettier, Playwright) — pinned when the dashboard package is scaffolded.

## Infrastructure

| Component      | Version          | Role                                                              |
| -------------- | ---------------- | ---------------------------------------------------------------- |
| PostgreSQL     | `postgres:18`    | Source of truth: businesses, customers, conversations, bookings, the calendar, and durable reminders. |
| Redis          | `redis:8`        | Ephemeral event bus / pub-sub (live dashboard updates, the approval gate) — **not** durable state. |
| Docker Compose | —                | Local dev and deployment topology (api, worker, dashboard, postgres, redis). |
| Make           | —                | The single entry point: `make up`, `make test`, `make check`, …  |
| GitHub Actions | —                | CI: the full gate (ruff, mypy, import-linter, pytest; dashboard typecheck/lint/test/build). |

## External APIs

| Service             | Interface                       | Notes                                                                                 |
| ------------------- | ------------------------------- | ------------------------------------------------------------------------------------- |
| WhatsApp            | Meta **WhatsApp Cloud API** (Graph API) | The only supported path for new integrations (the On-Premises API reached EOL in 2025). Pin the Graph API version against Meta's changelog when wiring it. |
| Telegram            | **Telegram Bot API** (~10.x)    | Standard `/bot<token>/<method>` HTTP interface.                                       |
| LLM provider        | HTTP (no vendor SDK)            | Anthropic / OpenAI / OpenAI-compatible, each an adapter behind one port (see [ADR-0006](./adr/0006-model-agnostic-llm-provider.md)). |

## Principles

Everything above serves [`CODING_PRINCIPLES.md`](../CODING_PRINCIPLES.md): typed,
testable, dependency-injected, with the domain core free of any of these
libraries. The stack lives at the edges; the core does not import it.
