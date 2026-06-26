# M2 — Business configuration API — report

**Status:** Done (2026-06-26) · [SaaS plan, Phase B](../plans/saas-telegram-plan.md)

A business can be configured entirely over HTTP — profile, services, hours, and the
LLM provider — no SQL.

## What was built

- **Repository writes**: `BusinessRepository.find/upsert`, `ServiceRepository.upsert/
  remove`, and a new `ResourceRepository` (ports, in-memory fakes, SQL adapters, shared
  port-contract suite).
- **Config API** (`config_api.py`): `/api/businesses/{id}` (profile + knowledge),
  `/services` (list / upsert / delete), `/resources` (list / upsert with working hours).
- **LLM provider API** (`business_config.py`, M2.1): `GET/PUT /api/businesses/{id}/llm`
  — platform default or own (openai / anthropic / openrouter) + model + key. The key is
  **write-only**: stored encrypted, never returned — only a 4-char hint. Inputs validated.

## Verification

- **Gate** (`make check`): ruff, mypy `--strict`, import-linter 3/3, **132 unit tests**,
  97.9 %.
- **Integration** (`logs/m1/integration.log`): the new write methods pass the port
  contracts on real Postgres — **14 integration tests**.
- **Real run** (`logs/m2/real-run.log`, live stack):
  1. Added a service (**Manicure**) to a business **via the API** (`PUT …/services/mani`).
  2. The assistant's menu **immediately reflected it** — “✂️ Haircut, 💅 Manicure”.
  3. The assistant **booked the API-added Manicure** → persisted in Postgres
     (`service_id=mani`).
  4. Setting an **own** provider key, `GET …/llm` returns `api_key_hint: "9999"` — the
     **full key is never in the response**.

## Definition of Done

- [x] A business + services + hours + knowledge + LLM provider can be created and
      edited entirely via the API.
- [x] Own-key and platform default both run the assistant (tenant resolution, M1).
- [x] The key never appears in any response (verified live) or log.
