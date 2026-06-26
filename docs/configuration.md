# Configuration

All configuration is read once from the environment into a typed `Settings` object
(`apps/api/src/frontdesk/core/settings.py`). Every value is a `FRONTDESK_*`
environment variable with a sensible default — set them in your shell, in
`apps/api/.env`, or (for the Docker stack) in `deploy/docker/.env` (see
[`deploy/docker/.env.example`](../deploy/docker/.env.example)).

The only one you usually need to set is `FRONTDESK_LLM_API_KEY`.

## Core

| Variable | Default | What it does |
| --- | --- | --- |
| `FRONTDESK_DATABASE_URL` | `postgresql+asyncpg://frontdesk:frontdesk@localhost:5432/frontdesk` | Async SQLAlchemy URL for Postgres. In the Docker stack the host is `postgres`. |
| `FRONTDESK_REDIS_URL` | `redis://localhost:6379/0` | Redis URL (events). |
| `FRONTDESK_LOG_LEVEL` | `INFO` | Log level. |

## LLM provider (model-agnostic)

| Variable | Default | What it does |
| --- | --- | --- |
| `FRONTDESK_LLM_PROVIDER` | `openai` | `openai` (any OpenAI-compatible endpoint) or `anthropic`. |
| `FRONTDESK_LLM_API_KEY` | _(empty)_ | **Required** to talk to a model. |
| `FRONTDESK_LLM_MODEL` | `deepseek/deepseek-v4-flash` | The model id. |
| `FRONTDESK_LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Endpoint (OpenAI provider only). Use `https://api.openai.com/v1`, a local server, etc. |
| `FRONTDESK_LLM_MAX_TOKENS` | `2048` | Completion budget. **Reasoning models need room to think *and* emit the tool call** — too small truncates before the call. |

Swapping models is config-only (see [ADR-0006](adr/0006-model-agnostic-llm-provider.md)).

## WhatsApp (Meta Cloud API)

Needed only to send/receive on real WhatsApp; without these the stack still runs
locally (replies are logged).

| Variable | What it does |
| --- | --- |
| `FRONTDESK_WHATSAPP_TOKEN` | Cloud API access token (outbound sends). |
| `FRONTDESK_WHATSAPP_PHONE_NUMBER_ID` | The sending phone-number id. |
| `FRONTDESK_WHATSAPP_APP_SECRET` | Verifies inbound `X-Hub-Signature-256`. |
| `FRONTDESK_WHATSAPP_VERIFY_TOKEN` | Echoed in the webhook verification handshake. |

## Telegram (Bot API)

| Variable | What it does |
| --- | --- |
| `FRONTDESK_TELEGRAM_TOKEN` | Bot token (outbound sends). |
| `FRONTDESK_TELEGRAM_SECRET` | Expected `X-Telegram-Bot-Api-Secret-Token` on inbound. |
| `FRONTDESK_TELEGRAM_BOT_ADDRESS` | The bot's own address, used for tenant resolution. |

## Demo & web chat

| Variable | Default | What it does |
| --- | --- | --- |
| `FRONTDESK_DEMO_TO_ADDRESS` | `+BIZ` | The business the web chat (`/api/chat`) talks to — matches the seeded channel binding. |
| `FRONTDESK_FIXED_NOW` | _(empty)_ | Freeze "now" (ISO 8601, e.g. `2026-06-26T09:00:00+00:00`) so demo slots don't drift. Empty = the real system clock (production). |
| `FRONTDESK_CORS_ALLOW_ORIGINS` | `*` | Comma-separated allowed origins for the browser dashboard. |

## A minimal `.env`

```dotenv
# the only thing you must set to see the assistant work
FRONTDESK_LLM_API_KEY=sk-or-...

# nice for a stable demo
FRONTDESK_FIXED_NOW=2026-06-26T09:00:00+00:00
```
