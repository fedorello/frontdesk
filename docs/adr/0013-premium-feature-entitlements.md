# ADR-0013: Premium-feature entitlements & operator management

**Status:** Accepted

> The hosted service is **tovayo.com**. This ADR covers a general **premium-feature
> entitlements** system — per-business access to sellable features — and the operator
> controls to grant/suspend it. It is the backbone for the voice receptionist and every
> future premium feature. Full design + plan:
> [`docs/plans/premium-features-plan.md`](../plans/premium-features-plan.md).

## Context

The platform is growing paid, closed-source features (the first is the voice receptionist,
which lives in the private `frontdesk-voice` repo). Each needs the same three things: a way
for a business to **get** it, a way for the operator to **manage** who has it, and a single
**gate** the feature checks before it runs. Building that per feature would duplicate
knowledge (§4) and bake feature names into the core (an OCP violation, §3.2).

Two constraints shape the decision:

- **Open-core.** The generic mechanism is reusable infrastructure and belongs in the open
  `frontdesk` repo; the premium features themselves (their implementation and billing) stay
  private. The open code must not import or hardcode "voice".
- **Admin is read-only today.** [ADR-0012](0012-admin-role-and-cross-tenant-analytics.md)
  deliberately scopes the platform operator to **aggregate, read-only** cross-tenant
  analytics. Managing entitlements means the operator now **writes** per-tenant state — a
  systemic change that needs its own decision (per CODING_PRINCIPLES §14).

## Decision

### A per-business entitlement, keyed by a config-driven feature registry

A `PremiumFeature` is a catalog entry (`key`, `name`, `description`, `pricing`) held in a
`FeatureRegistry` that is **built from configuration**, not code — adding a feature is a
config entry, never an enum edit (§3.2, §7.3). `FeatureKey` is a branded string validated
against the registry, so an unregistered key can never be silently allowed.

An `Entitlement` is one business's stake in one feature, moving through
`requested → active ↔ suspended` with an audit of `requested_at` / `decided_at`. A business
"has" a feature **iff** it holds an `active` entitlement. Persisted in a
`business_entitlement` table `(business_id, feature_key, status, requested_at, decided_at)`,
following the `role`-column precedent from ADR-0012.

### One gate, reused by every feature

`FeatureAccess.is_enabled(business_id, feature_key)` is the single check a feature calls
before serving. The private voice layer calls it at its endpoint and at number provisioning;
no feature ships its own ad-hoc gate.

### Self-serve request → operator approval

A business owner **requests** a feature (idempotent) through the owner-guarded API; the
request sits `requested` until an operator **approves** (`active`) or **suspends** it. This
matches the deferred billing: until pay-as-you-go charging exists, a granted feature is
active at no charge and the price is shown as "coming soon" (no hidden simulation, §8.1).

### Extending the admin surface to writes (the ADR-0012 exception)

The operator gains **write** endpoints — approve/suspend a business's feature — behind the
existing `make_admin_guard` (no new auth, §12). This is a deliberate, bounded relaxation of
ADR-0012's read-only rule: the writes touch **only** the `business_entitlement` row (never
customer data), reuse the same guard, and leave an audit trail (`decided_at`, plus a logged
decision for observability). The read-only analytics surface is unchanged.

### Open-core split

The open `frontdesk` repo owns the domain, ports, repository, use cases, the owner/admin
HTTP surface, and the dashboard UI — all feature-agnostic. The private `frontdesk-voice`
repo registers the `voice_receptionist` feature and enforces the entitlement; billing lives
there too. A landing demo captures a Google-signed-in visitor's email (`demo_lead`) before
revealing the demo numbers, protecting cost from anonymous abuse.

## Consequences

- **Good:** every future premium feature reuses the same registry, entitlement, gate, and
  operator controls — a new feature is config + a gate call, not a subsystem. The open core
  never learns about voice.
- **Cost:** the admin role is no longer purely read-only. Mitigated by the narrow write
  surface (one table), the shared guard, and the audit trail. If richer auditing or
  owner notifications are needed, a domain event on the decision is the natural extension.
- **Deferred:** pay-as-you-go charging is a later phase; until then entitlements grant
  access for free and the price copy reads "coming soon".
