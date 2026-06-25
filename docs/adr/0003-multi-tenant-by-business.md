# ADR-0003: Multi-tenant by business

**Status:** Accepted

## Context

One Frontdesk deployment should serve many businesses — a salon and a clinic and a
tutor — each with its own services, working hours, channels, knowledge base, and
calendar. Their data must never mix. We also want self-hosters to run a single
business cheaply without a different code path.

## Decision

Model the **Business** as the tenant. Every row that belongs to a business carries
its `business_id`, and every repository query is scoped to the current tenant. The
tenant is resolved from:

- **inbound channel** — which WhatsApp number / Telegram bot received the message
  maps to exactly one business; or
- **dashboard session** — the authenticated owner's business.

A single-business self-host is just a deployment with one tenant — same code.

## Consequences

- Strong isolation: no query crosses a `business_id` boundary; this is asserted in
  tests.
- The same binary scales from one business to many (SaaS or self-host).
- Tenant resolution is a small, explicit step at the edge (webhook / auth); the
  domain always operates within one business.
