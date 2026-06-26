# M1 — Tenant-aware backend — report

**Status:** Done (2026-06-26) · [SaaS plan, Phase A](../plans/saas-telegram-plan.md)

The foundation of the SaaS: one server, many businesses, each with its **own** bot
and model, secrets encrypted at rest.

## What was built

- **`SecretCipher`** port + `FernetCipher` adapter — authenticated encryption keyed by
  `FRONTDESK_SECRET_KEY`; stored bot tokens and API keys are never plaintext
  ([ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)).
- **Per-business config storage**: `telegram_bot` and `llm_config` tables (schema +
  idempotent migration 0002), DTOs + repository ports, in-memory fakes, and SQL
  adapters that **encrypt on write / decrypt on read**.
- **Tenant-aware resolution** (`interface/tenancy.py`): `provider_from_config` (a
  business's own OpenAI / Anthropic / OpenRouter key+model, or the platform default)
  and `telegram_messaging_from_config` / `TenantTelegramMessaging` (the business's own
  bot).
- **Multi-tenant Telegram webhook** `POST /webhooks/telegram/{business}` — routes by
  business, verifies the per-business secret, dispatches with that business's bot +
  provider. Wired into the production app; the worker sends each reminder via the
  right bot.

## Verification

- **Gate** (`make check`): ruff, mypy `--strict`, import-linter 3/3, **123 unit tests**,
  97.6 %.
- **Integration** (`logs/m1/integration.log`): the new SQL config repos pass the shared
  port-contract suite on real Postgres — **encryption roundtrips**; migration `0002`
  reaches head on a fresh DB with both tables.
- **Isolation, unit** (`test_telegram_webhook`): two businesses → two bots, in
  isolation; wrong secret 403; unknown business 404 — through real ASGI + the assistant
  loop + per-business provider.
- **Real run** (`logs/m1/real-run.log`, live Docker stack): two seeded businesses
  (`ana_bot` / `bob_bot`), a booking message to each webhook path → **two isolated
  appointments** in Postgres (`ana`→chat 55501, `bob`→chat 55502), booked by the real
  default model; wrong secret 403, unknown business 404.

## Honest caveat

The real-run **outbound** replies returned 500 because the seeded bot tokens are
**fake** (api.telegram.org 404). The booking commits before the send, so isolation is
proven; real BotFather tokens (M3) make the outbound 200. Outbound isolation itself is
proven in the unit test against a mock Telegram.

## Definition of Done

- [x] Two businesses, two different bots; each message answered by the right bot
      (unit, isolation) and each booking isolated in Postgres (real run).
- [x] A reminder is sent from the right business's bot (`TenantTelegramMessaging`, tested).
- [x] Secrets encrypted at rest; per-business secret verified; integration-tested.
