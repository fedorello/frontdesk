# ADR-0012: Admin role & cross-tenant analytics

**Status:** Accepted

> The hosted service is **tovayo.com**. This ADR covers a privileged **platform
> operator** role that reads aggregate analytics **across** all businesses — the one
> place where the strict per-tenant isolation of [ADR-0003](0003-multi-tenant-by-business.md)
> is deliberately relaxed. Full design: [`docs/design/admin-dashboard.md`](../design/admin-dashboard.md).

## Context

The platform operator needs to see the whole system at a glance: who signed up and when,
how many channels are connected, how many replies the assistant has sent, how many
appointments were booked, and the trends behind all of it. None of this is answerable
through the owner-scoped dashboard, because [ADR-0003](0003-multi-tenant-by-business.md)
scopes **every** query to one `business_id` and forbids a query crossing that boundary.

So we need exactly one actor that may read **across** tenants. That is a systemic
exception to ADR-0003 and therefore needs its own decision (per CODING_PRINCIPLES §14).
The risk to manage is privacy: cross-tenant reads must not become a console for browsing
one business's customers, phone numbers, or transcripts.

## Decision

### A second role, not a second auth system

Add a closed `UserRole` value set (`owner`, `admin`). An `account` gains a
`role` column (`text NOT NULL DEFAULT 'owner'`, `CHECK (role IN ('owner','admin'))`). An
**admin account owns no business** (`business_id` is `NULL`, already nullable). Admins
reuse the existing HMAC token + HttpOnly-cookie session unchanged — no custom auth
(§12). A new `make_admin_guard` verifies the session and requires `role = admin`; unlike
the owner guard it does **not** scope to a path `business_id`.

### Cross-tenant, but aggregate-only and read-only

The admin may read **only aggregates and per-business counts** — never message bodies,
customer addresses, or intake answers. This is enforced at the **port boundary**: the
analytics Protocols' return DTOs have no field that can carry customer PII, and there is
no admin endpoint that returns a transcript. The admin role is **read-only** — no writes,
no impersonation, no "log in as".

### Provisioning is out-of-band

Admin is granted only by an explicit, idempotent provisioning step (a script driven by a
`Settings` allowlist), never self-granted and never via a runtime `if email in [...]`
branch in the request path (§7.4). The request path checks the **stored DB role** only.

## Consequences

- Exactly one role crosses the ADR-0003 boundary, for aggregates only, read-only —
  the isolation guarantee still holds for owners and for all customer PII.
- The privacy boundary is structural (the DTOs can't carry PII), not a convention, so it
  can't be eroded by a careless endpoint.
- Cross-tenant aggregation is a new driven-port family
  (`PlatformSummaryRepository`, `PlatformTimeseriesRepository`,
  `BusinessDirectoryRepository`) with in-memory fakes and a SQL adapter — additive, behind
  Protocols, testable, and swappable.
- Admin access is an auditable DB fact (the `role` column), provisioned deliberately.

## Out of scope (for now)

Per-business drill-down into customer PII (a separate, consent-and-audit-gated feature),
write/impersonation actions, billing UI, and the event-sourced funnel analytics
(`analytics_event`) — left for a later phase. The ports leave room for each.
