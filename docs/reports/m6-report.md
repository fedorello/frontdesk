# M6 — Multilingual depth & SaaS hardening — report

**Status:** In progress (2026-06-26) · [SaaS plan, Phase F](../plans/saas-telegram-plan.md)

## Multilingual — already first-class

- **The assistant replies in the customer's language** — this works today: the LLM
  answers in the language the customer writes in, grounded on the business's real
  services/prices. No per-language code paths needed.
- **The dashboard is internationalized** in **en/es/ru/zh** (M5): catalog-driven, a
  language switcher, every new component string keyed — proven by unit + e2e tests
  that switch the UI to Russian.

## Hardening — cost control done

- **Daily quota on the managed default** (`UsageStore` + `usage_counter` table,
  migration 0004): each business on the platform-paid default is capped at
  `FRONTDESK_MANAGED_DEFAULT_DAILY_LIMIT` messages/day. Past the cap the Telegram
  webhook replies "limit reached" **without calling the LLM**; **own-key businesses
  are never capped**. Tested (the 2nd message past a limit of 1 is blocked before the
  LLM) + integration on real Postgres.

## Remaining hardening (post-MVP)

- **Auth lifecycle**: token expiry/refresh, login rate-limiting, email
  verification / magic links (M4 noted these).
- **Bot health**: webhook re-registration + a clear "bot offline" state, surfaced in
  the dashboard.
- **Usage metrics & billing seam**: surface the `usage_counter` to the owner; a hook
  for metered billing on the managed default.

## Definition of Done

- [x] The same bot serves customers in multiple languages (assistant replies in the
      customer's language).
- [x] The dashboard ships in the target locales (en/es/ru/zh).
- [x] A managed-default rate limit / cost control is in place.
- [ ] Bot-health checks + token rotation + a billing seam (post-MVP hardening).
