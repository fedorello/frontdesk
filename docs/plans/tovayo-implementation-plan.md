# Tovayo — implementation plan

The roadmap to turn the working Frontdesk codebase into **tovayo.com**: an
**open-source, self-serve, multi-tenant** AI receptionist for small businesses, where
an owner connects their own **Telegram** bot, configures their business, and either
brings their **own LLM provider/key** or uses our **managed default**. Multilingual
throughout.

This is the strategic plan (vision → architecture deltas → milestones → MVP). The
underlying decisions live in the ADRs, the per-phase backend detail in the
[SaaS plan](./saas-telegram-plan.md), and the screens in the
[UX brief](../design/ux-brief.md).

---

## The concept

- **Who:** small, appointment-based service businesses (salons, clinics, tutors,
  studios) that live on chat apps and lose money to missed messages and no-shows.
- **What:** a self-serve AI receptionist on **Telegram** that answers, books into a
  real calendar (no double-booking), reminds to kill no-shows, and escalates /
  gates anything sensitive (refunds) for human approval.
- **How it's sold:** open-source (self-host for free) **and** a hosted service at
  **tovayo.com**. Bring your own model + key, or use our default
  (OpenRouter · `deepseek/deepseek-v4-flash`).
- **Principle:** multilingual is first-class — the assistant speaks the customer's
  language; the dashboard speaks the owner's.

## What already exists (the foundation we build on)

The single-tenant product is **built, tested, and proven end to end** (see the
[main implementation plan](./implementation-plan.md), phases 0–9):

- A pure, tested **domain core** (availability, booking, no-double-book, reminders,
  state machines) behind ports & adapters.
- The **assistant** (LLM tool-use loop) — answers, books, reschedules, cancels,
  escalates, and gates refunds; grounded (never invents times, prices, services).
- **Real Postgres** persistence (gist exclusion constraint, `SKIP LOCKED` worker),
  **Telegram + WhatsApp** channel adapters + webhooks, the **reminder worker**, the
  **airlock** approval gate, a **Next.js dashboard**, a **web chat** (`/api/chat`), and
  a one-command **Docker stack**. Multi-tenant **inbound routing** already works.

So the SaaS is a layer **on top of** a working product — not a rewrite.

## What changes to become a SaaS

| Area | Today | Tovayo |
| --- | --- | --- |
| Outbound channel | one global bot token (env) | **per-business** bot token (encrypted, DB) |
| LLM provider | one global key (env) | **per-business** provider/key, or managed default |
| Webhook | one path | **routed by business** (`/webhooks/telegram/{business}`) |
| Configuration | SQL / seed | **self-serve write APIs + dashboard** |
| Accounts | none | **owner accounts**, strict per-tenant isolation |
| Secrets | env vars | **encrypted at rest** via a `SecretCipher` port (env → KMS) |
| Dashboard | demo data, English | **live data, internationalized** (en/es/ru/zh…) |

The core domain does **not** change. The work is tenant-awareness at the edges
(messaging + provider), self-serve configuration, accounts, secret storage, and an
internationalized UI.

---

## Milestones

Each milestone ends green against the gate and is verified with a real run. They map
to the [SaaS plan](./saas-telegram-plan.md) phases; here they're sequenced with
dependencies and an MVP cut.

### M1 — Tenant-aware backend ✅ _(done — [report](../reports/m1-report.md))_
Per-business secrets via a `SecretCipher` port (encrypt at rest, env key now;
[ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)). Make **outbound messaging**
and the **LLM provider** resolve **per business** at request time; route the Telegram
webhook by business. _(SaaS plan A.)_
**DoD:** two businesses, two bots, two models — each answered correctly and in
isolation; integration-tested.

### M2 — Business configuration API
Write APIs for profile (name, timezone, **default language**), services, hours,
knowledge, and **LLM provider** (default or own — encrypted key, validated on entry,
never returned/logged; [ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)).
_(SaaS plan B.)_
**DoD:** a business is fully configurable via API; own-key and default both run; the
key never appears in any response or log.

### M3 — Telegram self-serve connect
`Connect`: validate a bot token (`getMe`), store it encrypted, register the webhook
(`setWebhook` + per-business secret); `Disconnect`. _(SaaS plan C.)_
**DoD:** pasting a real BotFather token makes that bot answer and book, end to end.

### M4 — Accounts, auth & isolation _(depends on M2)_
Owner accounts (email + password / magic link), sessions, and **strict scoping** of
every write API and view to the owner's business. _(SaaS plan D.)_
**DoD:** an owner can't read or edit another business; tested.

### M5 — Dashboard: onboarding + management UI, internationalized _(depends on M2–M4; needs the designs)_
Implement the [UX brief](../design/ux-brief.md): sign up / log in, the onboarding
wizard (business → services → hours → knowledge → **choose AI** → **connect
Telegram**), and the live Overview / Conversations / Calendar / Approvals / Settings.
**i18n from the first screen** (catalogs per locale, language switcher, no hard-coded
strings). _(SaaS plan E.)_
**DoD:** a non-engineer signs up, configures, connects Telegram, and sees real
conversations/bookings — from the UI, in ≥2 languages; dashboard gate green + a
Playwright e2e of the onboarding happy path.

### M6 — Multilingual depth & SaaS hardening
Per-business default language on first contact and reminders; verify the assistant
answers each customer in their own language; translate the dashboard (en/es/ru/zh);
RTL-ready. Hardening: **quotas/rate limits on the managed default** (cost control),
bot-health checks, webhook re-registration, token rotation, basic usage metrics, and
a billing seam. _(SaaS plan F.)_
**DoD:** the same bot serves customers in multiple languages; the dashboard ships in
the target locales; default-path limits and bot health are in place.

---

## The MVP cut

The smallest thing worth shipping (**M1 → M5**, with M6 partial):

> A business owner signs up at tovayo.com, creates their business and one service,
> picks **default AI** (or pastes their own key), connects **their Telegram bot**, and
> a real customer books an appointment **in their own language** — with reminders and
> a refund held for approval. Self-hosters get the same from `docker compose`.

M6's depth (full locale set, billing, advanced limits) can follow the first release.

## Cross-cutting concerns

- **Secret storage** is a product feature, not a detail: encryption at rest, a KMS in
  production, write-only keys, no logging, validation, rotation — all behind the
  `SecretCipher` port ([ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)).
- **Cost control:** the managed default path is paid by the platform → per-tenant
  quotas/limits and a billing seam from M6. Own-key removes the limit.
- **Multilingual** is designed in from M2 (default language) and M5 (UI i18n), not
  bolted on.
- **Open-source parity:** one codebase serves self-host (env-key cipher, own default
  key) and hosted tovayo.com (KMS, metered default).

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Leaking a stored API/bot key | Encrypt at rest, write-only, never log, KMS in prod, validation + rotation. |
| Abuse of the managed default (cost) | Per-tenant quotas/rate limits; require own key past a threshold. |
| Tenant data crossing businesses | Isolation enforced at the boundary (M4) + tests; inbound already routes by tenant. |
| Telegram webhook/token drift | Health checks + re-registration (M6); clear "bot offline" state in the UI. |
| i18n retrofitted late | Internationalize the dashboard from the first screen (M5). |

## Out of scope (tracked for later)

WhatsApp onboarding (separate ADR), full billing/subscriptions, multiple team members
per business, additional LLM providers (Azure, Bedrock, local), and outbound
marketing. Every milestone leaves a clean seam.

## Where to look

- Decisions: [ADR-0008 (SaaS)](../adr/0008-multi-tenant-self-serve-saas.md) ·
  [ADR-0009 (BYO provider & secrets)](../adr/0009-byo-llm-provider-and-secrets.md).
- Backend phase detail: [SaaS plan](./saas-telegram-plan.md).
- Screens: [UX brief](../design/ux-brief.md).
- The existing product: [implementation plan](./implementation-plan.md).
