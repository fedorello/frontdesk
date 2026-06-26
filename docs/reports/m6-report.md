# M6 — Multilingual depth & SaaS hardening — report

**Status:** In progress (2026-06-26) · [SaaS plan, Phase F](../plans/saas-telegram-plan.md)

## Multilingual — already first-class

- **The assistant replies in the customer's language** — this works today: the LLM
  answers in the language the customer writes in, grounded on the business's real
  services/prices. No per-language code paths needed.
- **The dashboard is internationalized** in **en/es/ru/zh** (M5): catalog-driven, a
  language switcher, every new component string keyed — proven by unit + e2e tests
  that switch the UI to Russian.

## Hardening — done

- **Daily quota on the managed default** (`UsageStore` + `usage_counter` table,
  migration 0004): each business on the platform-paid default is capped at
  `FRONTDESK_MANAGED_DEFAULT_DAILY_LIMIT` messages/day. Past the cap the Telegram
  webhook replies "limit reached" **without calling the LLM**; **own-key businesses
  are never capped**. Tested (the 2nd message past a limit of 1 is blocked before the
  LLM) + integration.
- **Expiring session tokens**: tokens embed an issued-at and are rejected past
  `FRONTDESK_TOKEN_MAX_AGE_SECONDS` (default 7 days). Tested.
- **Bot-health check**: `GET …/telegram/health` calls `getMe` to confirm the stored
  token is still live (so the dashboard can show "bot offline").
- **Usage / billing seam**: `GET …/businesses/{id}/usage` returns today's count and
  the limit — the hook a metered-billing system reads. Tested.

## Remaining hardening (post-MVP)

- Login rate-limiting, email verification / magic links, token rotation (re-issue).
- Webhook auto re-registration on drift; surfacing bot-health + usage in the dashboard
  UI (endpoints exist; screens pending the designer).

## Definition of Done

- [x] The same bot serves customers in multiple languages (assistant replies in the
      customer's language).
- [x] The dashboard ships in the target locales (en/es/ru/zh).
- [x] A managed-default rate limit / cost control is in place.
- [x] Bot-health check, expiring tokens, and a usage/billing seam (endpoints) are in place.
- [ ] Surfacing health/usage in the dashboard UI + auto webhook re-registration (post-MVP; UI awaits the designer).
