# ADR-0008: Multi-tenant self-serve SaaS (Telegram-first, multilingual)

**Status:** Accepted (planning) — see [the SaaS plan](../plans/saas-telegram-plan.md)

## Context

Frontdesk already works as a multi-tenant product: the domain, booking, reminders,
and approvals are all keyed by `business_id`, and **inbound** messages are routed to
the right business by the address they were sent _to_
([ADR-0003](0003-multi-tenant-by-business.md)). What's missing to make it a
**self-serve SaaS** — where a business owner sets up their own AI receptionist on
Telegram without an engineer — are three things:

1. **Per-tenant channel credentials.** Today outbound replies use a single global
   bot token from the environment, and `channel_binding` stores only
   `(channel, address, business_id)` — no token or secret. Every business needs its
   **own** Telegram bot.
2. **Self-serve onboarding.** A business owner must be able to sign up, define their
   services / hours / knowledge, and connect their channel through the dashboard —
   not via SQL.
3. **Accounts & isolation.** Owners log in and only ever see and edit their own
   business.

Two product constraints frame this ADR:

- **Telegram first.** Telegram self-serve is achievable now (the owner creates a bot
  via BotFather and pastes the token). WhatsApp Cloud API requires per-business Meta
  apps / Embedded Signup through a Business Solution Provider — a much larger effort,
  deferred to a separate ADR.
- **Multilingual is a first-class requirement,** not an afterthought. Customers and
  business owners span languages; both the assistant's replies **and** the dashboard
  must work in several languages.

## Decision

Build the SaaS layer on top of the existing hexagon, changing as little of the core
as possible. The core stays language- and channel-agnostic; everything tenant- and
locale-specific lives in adapters and configuration.

**1. Tenant-aware outbound.** Store each business's Telegram credentials (bot token,
webhook secret, bot username) in the database, encrypted at rest. Introduce a
`ChannelConfigRepository` port; the webhook handler and the reminder worker build the
**per-business** messaging adapter from the stored token, instead of a global one.
Outbound therefore always goes through that business's own bot.

**2. Webhook routing by business.** Each bot's Telegram webhook points at a
per-business path (`POST /webhooks/telegram/{business}`) with a per-business secret
token. The handler resolves the business from the path, verifies the secret, and
dispatches with that business's outbound adapter.

**3. Self-serve onboarding.** Add write APIs for business profile, services, working
hours, knowledge base, and a **Connect Telegram** action that validates the token
(`getMe`), stores it encrypted, and registers the webhook (`setWebhook`). The
dashboard drives these.

**4. Accounts & scoping.** Owner accounts (auth), with every write API and dashboard
view scoped to the owner's business. (A business may later have multiple members.)

**5. Multilingual, two layers.**
- **Assistant ↔ customer:** already replies in the customer's language; each business
  has a **default language** for first contact and reminders, and the knowledge base
  is authored in the owner's language and answered in the customer's.
- **Dashboard ↔ owner:** internationalized UI (the same approach used elsewhere —
  message catalogs per locale, locale negotiation, a language switcher), built
  multilingual from the first screen, with room for longer translations and RTL.

**6. Secrets at rest.** Bot tokens and webhook secrets are encrypted with a key from
the environment (`FRONTDESK_SECRET_KEY`); they are never logged or returned by the
API in full.

## Consequences

- The biggest change is that **outbound messaging becomes tenant-aware** — a clean,
  contained change behind the existing `MessagingPort` (the webhook and worker pick
  the adapter per business). The domain core does not change.
- One deployment serves many businesses, each with its own bot, its own calendar,
  its own approvals — true SaaS isolation, enforced by the architecture.
- Telegram-only narrows the onboarding surface to something a non-engineer can
  actually complete (create bot → paste token). WhatsApp remains a future ADR.
- Storing third-party tokens raises the security bar: encryption at rest, careful
  logging, and rotation become part of the product, not optional.
- Multilingual from day one costs some discipline (no hard-coded UI strings, catalogs
  per locale) but is far cheaper than retrofitting it later.

## Out of scope (for now)

WhatsApp onboarding, billing/subscriptions, team members per business, and outbound
marketing. The plan leaves clean seams for each.
