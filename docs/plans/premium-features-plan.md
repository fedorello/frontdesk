# Premium Features & Entitlements — Design & Implementation Plan

> Status: **planned** (not started). This document is the spec + inside-out build plan for a
> general **premium-feature management system**, and its first consumer: the **voice receptionist**
> (landing demo, self-serve request, admin management, entitlement gating).
>
> It follows [`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md) and the hexagonal architecture in
> [`docs/architecture/overview.md`](../architecture/overview.md). It mirrors the shape of
> [`admin-dashboard-plan.md`](./admin-dashboard-plan.md).

## 1. Goal

Let the platform sell and manage **premium features** per business, generically, so that adding the
next premium feature is a *registration + config* change — never a rewrite of the core (OCP, §3.2).
The first feature is the **voice receptionist** (premium, closed-source, in `frontdesk-voice`).

Concretely, we must deliver:

1. A **general entitlements system**: which premium features a business has, requestable and
   grantable, enforced by a single gate reused by every feature.
2. A **landing demo** of the voice feature on tovayo.com: 3 language demo numbers (EN/RU/ES),
   revealed **only after Google sign-in** (to capture the visitor's email as a lead), with a
   **"pay-as-you-go — $1 / call — coming soon"** call to action (payment is not built yet).
3. A **self-serve request → admin approval** flow for a business to get the feature.
4. **Admin management** controls (approve / suspend a feature per business).

## 2. Product decisions (locked)

| Decision | Choice |
|---|---|
| How a business gets a feature | **Self-serve request → admin approval.** Owner requests; operator approves. |
| Demo numbers on the public landing | **Google-sign-in gated.** Numbers are revealed only to a Google-authenticated visitor; the email is stored as a lead. Protects our TTS/telephony budget from anonymous abuse. |
| Voice pricing shown | **Pay-as-you-go, $1 / call.** Displayed as **"coming soon"** — no payment is processed yet (§8.1: simulation is forbidden; the CTA is explicitly "coming soon"). |
| Billing / charging | **Deferred** (own phase, later). Until then a granted feature is simply active at no charge. |

## 3. Architecture

### 3.1 Where the code lives (open-core)

The **entitlement system is generic infrastructure → the open `frontdesk` repo** (`apps/api`,
`apps/dashboard`, `apps/web`). The **voice feature's enforcement, provisioning and billing stay in
the private `frontdesk-voice` repo**. The clean line:

- **Open** (reusable by any premium feature): the domain model, the feature registry, the
  entitlement repository + use cases, the owner/admin/demo HTTP surface, and the dashboard/landing
  UI. This code never imports or hardcodes "voice".
- **Private** (`frontdesk-voice`): reads the shared entitlement table via the same
  `FeatureAccess` gate to allow/deny a call, and (later) does pay-as-you-go billing.

The catalog of *which* premium features exist and their display copy is **config-driven** (§7.3),
so the open code stays feature-agnostic and the tovayo deployment declares the `voice_receptionist`
feature in configuration — adding a feature never edits an enum or a `switch`.

### 3.2 Domain (pure, in `apps/api/src/frontdesk/domain/`)

```python
FeatureKey = NewType("FeatureKey", str)   # branded, validated against the registry (§2.3)

class EntitlementStatus(StrEnum):         # §7.2 no magic strings
    REQUESTED = "requested"   # owner asked, awaiting an operator
    ACTIVE    = "active"      # granted — the feature works
    SUSPENDED = "suspended"   # turned off by an operator

@dataclass(frozen=True, slots=True)
class PremiumFeature:                      # a catalog entry (registry value)
    key: FeatureKey
    name: str
    description: str
    pricing: str                          # display copy, e.g. "$1 per call"

@dataclass(frozen=True, slots=True)
class Entitlement:                         # one business's stake in one feature
    business_id: BusinessId
    feature_key: FeatureKey
    status: EntitlementStatus
    requested_at: datetime                 # tz-aware UTC (§7.7)
    decided_at: datetime | None = None     # when an operator last approved/suspended
```

Invariants (unit-tested): a business "has" a feature iff an `Entitlement` exists with
`status == ACTIVE`; status transitions are `REQUESTED→ACTIVE`, `ACTIVE↔SUSPENDED`,
`REQUESTED→SUSPENDED` (a rejected request). A transition method on the entity returns a new frozen
`Entitlement` (no in-place mutation).

### 3.3 Feature registry (config-driven, OCP)

`FeatureRegistry` wraps `dict[FeatureKey, PremiumFeature]`, built once at composition from a config
list of feature definitions (a `Settings`-provided structure, §7.3). It exposes `all()` and
`get(key) -> PremiumFeature | None`, and validates that any `FeatureKey` crossing a boundary is
registered (unknown key → domain error). Adding a feature = a new config entry (OCP §3.2).

### 3.4 Ports (Protocols in `application/ports.py`, ISP-split §3.4)

- `EntitlementRepository` (the hot read + the write):
  - `active_features(business_id) -> frozenset[FeatureKey]`
  - `get(business_id, feature_key) -> Entitlement | None`
  - `save(entitlement) -> None`
- `EntitlementDirectory` (operator read views, kept separate from the hot path):
  - `pending() -> tuple[Entitlement, ...]`
  - `for_business(business_id) -> tuple[Entitlement, ...]`
- `DemoLeadRepository` (landing lead capture):
  - `record(lead: DemoLead) -> None`

Each gets an **in-memory fake** (§6.1.7) reused across tests and a Postgres adapter.

### 3.5 Use cases (application, one responsibility each §3.1)

- `FeatureAccess.is_enabled(business_id, feature_key) -> bool` — **the single gate** every premium
  feature calls. Reads `active_features`. (Voice calls this from the private layer.)
- `FeatureCatalog.for_business(business_id) -> tuple[FeatureView, ...]` — the registered features
  joined with this business's status, for the dashboard.
- `RequestFeature.execute(business_id, feature_key)` — owner action: upsert a `REQUESTED`
  entitlement (idempotent; a re-request on an ACTIVE/SUSPENDED one is a no-op / re-open per rules).
- `ReviewFeatureRequest.approve(...)` / `.suspend(...)` — operator actions: transition status,
  stamp `decided_at` via the injected `Clock`, publish a domain event.
- `RecordDemoLead.execute(email, feature_key) -> tuple[str, ...]` — verify already happened at the
  edge; store the lead and return the configured demo numbers.

### 3.6 Persistence (Postgres)

New tables (DDL in `infrastructure/postgres/schema.py`, one Alembic migration each — schema only,
no logic §12):

- `business_entitlement`:
  `business_id text NOT NULL REFERENCES business(id)`, `feature_key text NOT NULL`,
  `status text NOT NULL CHECK (status IN ('requested','active','suspended'))`,
  `requested_at timestamptz NOT NULL`, `decided_at timestamptz NULL`,
  `PRIMARY KEY (business_id, feature_key)`. (`feature_key` validated in the domain against the
  registry, not by FK — features are config, not rows.)
- `demo_lead`:
  `id text PK`, `email text NOT NULL`, `feature_key text NOT NULL`,
  `created_at timestamptz NOT NULL`. (Lead capture from the landing.)

Follows the existing `role` precedent (enum + CHECK column + migration `0021` + Sql adapter).

## 4. HTTP surface

### 4.1 Owner (behind the existing per-tenant owner guard, `auth.py`)

- `GET  /api/features` → the catalog for the caller's business: `[{key, name, description, pricing,
  status}]`.
- `POST /api/features/{key}/request` → create/re-open a `REQUESTED` entitlement. 409 on unknown key.

### 4.2 Admin (behind `require_admin`, `admin_api.py`; **this adds writes → ADR-0013**)

- `GET /api/admin/entitlements?status=requested` → pending requests across tenants.
- `GET /api/admin/businesses/{id}/features` → that business's features + statuses.
- `PUT /api/admin/businesses/{id}/features/{key}` `{status: active|suspended}` → approve / suspend.

### 4.3 Demo lead (public, on the marketing origin)

- `POST /api/demo/voice-access` `{google_credential}` → verify the Google ID token (reuse the
  dashboard's Google verification, `google_auth.py`), `RecordDemoLead`, return
  `{numbers: [{lang, e164, label}]}` (numbers from config). Rate-limited (§ security).

## 5. Frontend

### 5.1 Dashboard — owner (`apps/dashboard`, Next.js)

A **"Premium features"** view in settings: each registered feature as a card with its pricing and a
state machine — `Request access` → `Requested (pending review)` → `Active`. Uses the existing
`api.ts` client pattern + `ui/` components (`Card`, `ToggleSwitch`, `ConfirmModal`). i18n keys in all
four locales.

### 5.2 Dashboard — admin (`apps/dashboard/app/admin/`)

A **"Feature requests"** admin page (pending list, approve/suspend) and per-business feature toggles
on the business detail. Reuses the `loading | denied | ready` pattern and `ToggleSwitch`. The client
gate is UX only; `require_admin` is the real gate.

### 5.3 Landing — Google-gated demo (`apps/web`, marketing)

A new `VoicePremium()` section in `app/page.tsx`, slotted after `Features`:

- Before sign-in: headline + "Sign in with Google to try the live demo" (Google Identity Services
  button). Copy in `i18n.tsx` (en/es/ru/zh).
- After sign-in: reveal the **3 demo numbers** (EN/RU/ES) as cards + the
  **"Pay-as-you-go · $1 / call · Coming soon"** banner (mirrors `CtaBanner`/`RunCard`).
- The sign-in posts the Google credential to `/api/demo/voice-access`; the email is stored as a lead
  and the numbers come back from the backend (never hardcoded in the client — numbers are config).

> Note: `apps/web` has no auth or API client today and no test setup. This phase adds a minimal
> Google sign-in + one fetch, and backend tests cover the endpoint; the web section is verified
> manually + (optionally) a Playwright smoke like the dashboard.

## 6. ADR to record

**ADR-0013 — Premium-feature entitlements & operator management.** Records: (a) the per-business
entitlement model and config-driven feature registry; (b) that the admin surface gains **write**
actions (approve/suspend), **extending ADR-0012's read-only admin scope** — with the rationale,
the guard reuse (`require_admin`), and the audit trail (`decided_at` + domain event). Written in
Phase 3, before the admin writes merge.

## 7. Inside-out phased plan

Each phase: full local gate green (`ruff`, `mypy --strict`, `import-linter`, `pytest ≥90%`),
Conventional Commits, and a tagged `frontdesk` release where the private voice layer must consume it.

### Phase 1 — Entitlement core (open) — *no behavior change*
- **Domain:** `FeatureKey`, `EntitlementStatus`, `PremiumFeature`, `Entitlement` (+ transition
  rules), `FeatureRegistry`, unknown-key domain error. Config schema for feature definitions +
  demo numbers in `core/settings.py`.
- **Ports + fakes:** `EntitlementRepository`, `EntitlementDirectory`, `DemoLeadRepository` +
  in-memory fakes.
- **Persistence:** `business_entitlement` + `demo_lead` DDL, two Alembic migrations, Sql adapters.
- **Use case:** `FeatureAccess.is_enabled`.
- **Tests:** domain invariants + transitions, registry validation, Sql adapters (integration),
  `FeatureAccess`. **DoD:** ≥90% on new code; nothing gated yet.

### Phase 2 — Owner request + catalog (open)
- Use cases `RequestFeature`, `FeatureCatalog`; owner API `GET /api/features`,
  `POST /api/features/{key}/request`; dashboard "Premium features" view + i18n.
- **Tests:** use cases (incl. idempotent re-request), API integration, dashboard component
  (`loading|empty|ready`, request→pending). **DoD:** an owner can request; status shows pending.

### Phase 3 — Admin management + ADR-0013 (open)
- `EntitlementDirectory`; use case `ReviewFeatureRequest` (approve/suspend + event); admin API
  (list pending, per-business, `PUT` status); admin dashboard "Feature requests" page + toggles.
  **Write ADR-0013.**
- **Tests:** transitions (approve/suspend/reject), admin API behind guard (401/403/200), admin page.
  **DoD:** operator approves a request → the business's entitlement becomes ACTIVE.

### Phase 4 — Google-gated landing demo + lead capture (open)
- Backend: `RecordDemoLead`, `POST /api/demo/voice-access` (Google verify + lead + config numbers),
  rate limit. Frontend: `VoicePremium()` section in `apps/web` with Google sign-in gate + numbers +
  "$1/call — coming soon"; i18n in 4 locales.
- **Tests:** endpoint (valid/invalid token, lead stored, numbers returned), rate limit. Web section
  manual + optional Playwright smoke. **DoD:** a Google-signed-in visitor sees the 3 numbers; the
  email is captured; anonymous visitors see only the sign-in CTA.

### Phase 5 — Voice enforcement (private `frontdesk-voice`)
- Register the `voice_receptionist` feature (config). Gate `/chat/completions` and number
  provisioning on `FeatureAccess.is_enabled(business_id, VOICE_KEY)`; deny → a spoken "not enabled"
  or 402 at provisioning. Re-pin the tagged `frontdesk`.
- **Tests (private repo):** enabled → serves; not enabled → denied. **DoD:** voice is Pro-gated;
  a business without the active entitlement cannot use the voice endpoint.

### Phase 6 — Pay-as-you-go billing (deferred)
- Replace "coming soon" with real per-call charging ($1/call), metered from Vapi call records, in
  the private layer. Out of scope here; tracked as a follow-up. Until shipped, the CTA stays
  "coming soon" and granted features are free.

## 8. Non-goals (this plan)

- Real payment / charging (Phase 6, deferred).
- Per-seat / per-user entitlements — entitlements are **per business**.
- Usage metering dashboards for voice (separate work; the `usage_counter` seam already exists).

## 9. Risks & mitigations

- **Public demo cost abuse** → mitigated by the Google-sign-in gate + endpoint rate limit; demo
  numbers never appear in anonymous HTML.
- **Admin writes vs ADR-0012 read-only scope** → resolved by ADR-0013 with an audit trail.
- **Open-core leakage** → the open code stays feature-agnostic; "voice" appears only in config and
  in the private `frontdesk-voice` layer.
- **Weak-model / TTS quota** (existing) → orthogonal; unaffected by this plan.
