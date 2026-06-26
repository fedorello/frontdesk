# SaaS plan — self-serve, multi-tenant, Telegram-first, multilingual

The plan to turn Frontdesk into a self-serve SaaS where a business owner sets up
their own AI receptionist on Telegram. Built on the existing hexagon
([ADR-0008](../adr/0008-multi-tenant-self-serve-saas.md)); the domain core does not
change. **Telegram only** for now; **multilingual** throughout. Every phase ends
green against the gate and is verified with a real run.

## Status

| Phase | Title | Status |
| --- | --- | --- |
| A | Per-tenant Telegram + tenant-aware outbound | ✅ Done — [report](../reports/m1-report.md) |
| B | Business configuration write-API | ✅ Done — [report](../reports/m2-report.md) |
| C | Telegram self-serve connect | ✅ Code-complete — [report](../reports/m3-report.md) |
| D | Accounts, auth & tenant scoping | ✅ Done — [report](../reports/m4-report.md) |
| E | Dashboard: onboarding + management UI (i18n) | 🟡 Functional core — [report](../reports/m5-report.md) |
| F | Multilingual depth & SaaS hardening | 🟡 In progress — [report](../reports/m6-report.md) |

---

## Phase A — Per-tenant Telegram + tenant-aware outbound

**Goal:** every business replies through **its own** bot; one server, many bots.

- Schema + migration: a `telegram_bot` config per business — `business_id`,
  `bot_token` (encrypted), `secret_token`, `username`, `webhook_set`.
- A `SecretCipher` port for **all** stored secrets (bot tokens *and* LLM keys) —
  authenticated encryption with an env key now, a KMS adapter later
  ([ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)). Key: `FRONTDESK_SECRET_KEY`.
- A `ChannelConfigRepository` port + SQL adapter (get a business's Telegram config).
- Make outbound **tenant-aware**: the webhook handler and the reminder worker build
  the per-business Telegram messaging adapter from the stored token (instead of the
  global env token).
- Route inbound by business: `POST /webhooks/telegram/{business}` — resolve the
  business from the path, verify its secret token, dispatch with its outbound adapter.

**DoD:** two businesses with two different bots; a message to each is answered by the
right bot; a reminder is sent from the right bot; integration test proves isolation.

## Phase B — Business configuration write-API

**Goal:** a business can be fully configured over the API (no SQL).

- Write endpoints (scoped later in Phase D): create/update business profile
  (name, timezone, **default language**), services (name, duration, price), working
  hours, resources, and knowledge-base entries.
- **Bring-your-own LLM provider** ([ADR-0009](../adr/0009-byo-llm-provider-and-secrets.md)):
  an `llm_config` per business — `mode` (platform default *or* own), `provider`
  (openai · anthropic · openrouter), `model`, and an **encrypted** `api_key`. The
  provider is resolved **per business** at request time; `default` uses the platform's
  OpenRouter + `deepseek-v4-flash`. The key is encrypted via `SecretCipher`, validated
  on entry (one cheap call), **never returned or logged** (only `{provider, model,
  hint}` is exposed).
- Validation in the application layer; the domain rules are unchanged.

**DoD:** a business + services + hours + knowledge + LLM provider can be created and
edited entirely via the API; a business using its **own** key runs the assistant on
its own model, and one on `default` runs on the platform model — both verified; the
key never appears in any response or log.

## Phase C — Telegram self-serve connect

**Goal:** an owner connects their own bot in one step.

- `Connect Telegram`: accept a bot token, validate it (`getMe`), store it encrypted,
  generate a webhook secret, and register the webhook (`setWebhook` with the
  per-business URL + secret). A `Disconnect` that calls `deleteWebhook`.
- Surface connection status and the bot username; never return the full token.

**DoD:** pasting a real BotFfrom token makes that bot live — it answers and books —
end to end, verified with a real bot.

## Phase D — Accounts, auth & tenant scoping

**Goal:** owners log in and only touch their own business.

- Owner accounts (email + password or magic link), sessions/tokens, password
  handling.
- Scope every write API and dashboard view to the authenticated owner's business;
  enforce isolation at the boundary.

**DoD:** an owner signs up, creates a business, and cannot read or edit another
business; covered by tests.

## Phase E — Dashboard: onboarding + management UI (internationalized)

**Goal:** a non-engineer does everything from the browser, in their language.

- Internationalize the dashboard from the first screen (message catalogs per locale,
  locale negotiation, a language switcher) — no hard-coded user-facing strings.
- Build the screens from the [UX brief](../design/ux-brief.md): sign up / log in, the
  onboarding wizard (business → services → hours → knowledge → connect Telegram),
  conversations, calendar, approvals, and settings.
- Wire the screens to the Phase B–D APIs.

**DoD:** a new owner signs up, configures their business, connects Telegram, and sees
real conversations/bookings — all from the UI, in at least two languages; the
dashboard gate (typecheck, lint, test, build) is green and a Playwright e2e covers
the onboarding happy path.

## Phase F — Multilingual depth & SaaS hardening

**Goal:** polish the multilingual experience and the operational edges.

- Per-business default language applied to first contact and reminders; verify the
  assistant answers each customer in their own language; handle longer translations
  and RTL.
- Translate the dashboard into the target locales (en/es/ru/zh to start).
- Hardening: per-tenant rate limits, webhook re-registration/health, token rotation,
  basic usage metrics, and clear seams for billing.

**DoD:** the assistant demonstrably serves customers in multiple languages from the
same bot; the dashboard ships in the target locales; rate limiting and bot-health
checks are in place.

## Out of scope (tracked for later)

WhatsApp onboarding (separate ADR), billing/subscriptions, multiple team members per
business, and outbound campaigns. Each phase leaves a clean seam.
