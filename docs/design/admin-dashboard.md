# Admin Dashboard & Admin Role — Design

> A platform operator (Fedor) signs in and sees the whole business at a glance: who
> signed up and when, how many bots are connected, how many replies the receptionist
> agent has sent, how many appointments were booked, and the trends behind all of it —
> with charts, sortable tables, and an activation funnel.

**Status:** design. Nothing implemented yet. Targets `main`.

This document is written to comply with [`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md)
**by construction** — every section names the layer it touches, the Protocol it adds, the
constants/enums that replace magic values, and the tests that gate it. Where the feature
must cross an existing architectural boundary (one role reading across tenants), that is
called out as an explicit, ADR-worthy exception, never a quiet hack.

---

## 1. Goals / non-goals

### Goals

- A new **`admin` role** — a platform operator account, distinct from a business owner,
  that can read **cross-tenant** aggregate analytics.
- An **admin dashboard** in the existing Next.js app showing:
  - signups over time (who registered, when);
  - connected channels (Telegram bots, owner-notification links);
  - agent activity (assistant replies over time, totals);
  - bookings (totals, by status, over time, no-show / cancellation rates);
  - usage of the managed-default LLM (a cost proxy);
  - a per-business directory (sortable, searchable, server-paginated);
  - an **activation funnel**: signup → bot connected → first message → first booking.
- Charts that are clear, themeable, and accessible (SVG, no emojis — §7.12).

### Non-goals (v1)

- **No cross-tenant access to raw customer PII** — no reading another business's
  transcripts, customer phone numbers, or intake answers from the admin console. The
  admin sees **aggregates and counts**, not personal data. (This is a hard privacy
  boundary — see §4.4. Per-business drill-down into PII, if ever wanted, is a separate,
  consent-and-audit-gated feature, not this one.)
- No write/impersonation actions on tenants (no "log in as", no editing a tenant's
  config). v1 is **read-only**.
- No billing/invoicing UI (the usage numbers are a seam for it later, not the feature).

---

## 2. What "useful information" means here — the metric catalogue

Every metric below names its **data source** so the design is grounded in the schema we
already have (`infrastructure/postgres/schema.py`), plus the few additive columns in §3.

### 2.1 Headline KPIs (overview cards)

| KPI | Source |
|---|---|
| Total businesses | `count(business)` |
| New signups — today / 7d / 30d | `account.created_at` (new column, §3) |
| Active businesses (activity in 30d) | distinct `message.business_id` where `at >= now-30d` |
| Total customers | `count(customer)` |
| Total appointments | `count(appointment)` |
| Appointments by status | `appointment` grouped by `status` |
| No-show rate / cancellation rate | derived in the use case from the status counts |
| Total agent replies | `count(message)` where `role = 'assistant'` |
| Connected Telegram bots | `count(telegram_bot)` |
| Owner-notification links | `count(owner_telegram_link)` |
| Managed-default vs own LLM | `llm_config` grouped by `mode` |
| Pending approvals (all tenants) | `count(approval)` where `status = 'pending'` |

### 2.2 Time-series (charts)

Each is a list of `(day, count)` over a requested window, bucketed by UTC day:

- **Signups per day** — `account.created_at`.
- **Agent replies per day** — `message` where `role = 'assistant'`, by `at`.
- **Bookings created per day** — `appointment.created_at` (new column, §3). Optionally a
  second series **bookings by appointment date** (`starts_at`) for load planning.
- **New customers per day** — `customer.created_at` (new column, §3).
- **Managed LLM calls per day** — `usage_counter (day, count)` summed across businesses
  (already a daily counter — a natural time series, no new storage).

> **Why `assistant` replies need no new table.** The `message` table already stores every
> turn with a role and a `timestamptz at`. Counting `role='assistant'` answers "how many
> replies did the agent make" exactly, with no duplication of truth (DRY §4).

### 2.3 Activation funnel

A four-stage funnel computed per business and aggregated:

1. **Signed up** — has an `account`.
2. **Connected a bot** — has a `telegram_bot` (or any `channel_binding`).
3. **Received a first message** — has ≥1 `message` with `role='customer'`.
4. **Got a first booking** — has ≥1 `appointment`.

This is the single most useful operator view for a self-serve SaaS (where do new
businesses stall), and it falls out of the same tables.

### 2.4 Business directory (table)

One row per business, **server-paginated and sortable** (mirrors the existing
server-side pagination in `read_api.list_appointments`):

`name · signup date · locale · timezone · #services · #customers · #appointments
(by status) · #agent replies · last activity · bot connected? · LLM mode · owner
Telegram linked?`

No customer PII in this table — only counts and the business's own config.

---

## 3. Data-model gaps & migrations

Most metrics come from existing tables. Three are **not** answerable today because the
rows carry no creation timestamp. We add them honestly rather than approximate.

| Table | Add | Unlocks |
|---|---|---|
| `account` | `created_at timestamptz NOT NULL DEFAULT now()` | signups over time |
| `appointment` | `created_at timestamptz NOT NULL DEFAULT now()` | bookings-created over time (distinct from the appointment's `starts_at`) |
| `customer` | `created_at timestamptz NOT NULL DEFAULT now()` | new-customers over time |

Notes:

- One Alembic migration per logical change (the repo's convention — see
  `alembic/versions/`), and the same DDL mirrored into
  `infrastructure/postgres/schema.py` so the migration and the integration-test schema
  never drift (the file's stated contract).
- All columns are `TIMESTAMPTZ` with `DEFAULT now()` — UTC-aware, never naive (§7.7).
  This follows the **existing precedent in this very schema**: `approval.created_at` and
  `owner_telegram_link.linked_at` are already DB-managed `timestamptz ... DEFAULT now()`.
- **`created_at` is a persistence-only column, NOT a field on the pure domain models.**
  "When the row was inserted" is an operational/analytics fact, not a business rule, so
  `Account` / `Appointment` / `Customer` stay pure and unchanged (KISS/YAGNI — we don't
  thread a timestamp through dozens of construction sites). The analytics repository reads
  the column directly in SQL; the domain never reconstructs it.
- **Backfill caveat (stated, not hidden):** existing rows get `now()` as their
  `created_at`, so historical pre-migration signups/bookings collapse onto the migration
  date. The charts are accurate from the migration forward. This is acceptable for an
  internal operator tool and is noted in the migration's docstring (no silent fudging —
  §8.1).

### 3.1 Indexes for the aggregations

Aggregations must run in SQL, not by pulling rows into Python (§1 perf, but only after
correctness/testability). Add covering indexes so the GROUP BYs stay cheap:

- `account (created_at)`, `appointment (created_at)`, `customer (created_at)`
- `message (role, at)` and `message (business_id, role)` for reply counts per day / per
  business
- existing `approval (business_id, status)` already covers pending counts.

---

## 4. The admin role

### 4.1 The role itself (domain)

There is no role concept today: an `Account` owns exactly one `Business`
(`business_id`, already **nullable**). We add a closed value set, not a magic string
(§7.2):

```python
# domain/enums.py
class UserRole(StrEnum):
    OWNER = "owner"   # a business owner — the only role today
    ADMIN = "admin"   # a platform operator: cross-tenant, read-only analytics
```

```python
# application/ports.py — Account gains:
role: UserRole = UserRole.OWNER
```

An **admin account has `business_id = None`** (it owns no tenant) and `role = ADMIN`.

`account` table gains:

```sql
role text NOT NULL DEFAULT 'owner'
    CHECK (role IN ('owner', 'admin'))
```

The `CHECK` whitelist mirrors the locale-column pattern the principles call for (§7.8).

### 4.2 The admin guard (interface)

A new guard alongside `make_owner_guard`, reusing the same verified-account helper:

```python
# interface/auth.py
def make_admin_guard(
    accounts: AccountRepository, key: str, max_age: int = 0
) -> Callable[..., Awaitable[None]]:
    """Require the caller's session to belong to an ADMIN account. Cross-tenant:
    unlike the owner guard, it does NOT scope to a path business_id."""
    async def guard(session: str = Cookie(default="", alias=SESSION_COOKIE),
                    authorization: str = Header(default="")) -> None:
        token = session or authorization.removeprefix("Bearer ").strip()
        account = await _verified_account(token, accounts, key, max_age)
        if account is None or account.role is not UserRole.ADMIN:
            _logger.warning("admin auth rejected")   # no PII (§ security)
            raise HTTPException(403, "admin only")
    return guard
```

It reuses the existing HMAC token + HttpOnly-cookie machinery unchanged (`security.py`,
`cookies.py`) — same session, new authorization check. No custom auth (§12).

### 4.3 Bootstrapping the first admin (no hacks)

Admin is a privileged role, so it is **provisioned out-of-band**, never self-granted and
never a runtime `if email in [...]` branch in request handling (that would be both an
OCP/§7.4 smell and a security footgun).

- A config allowlist, read via `Settings` (§7.3), default empty:
  ```python
  admin_emails: str = ""   # comma-separated; consumed ONLY by the promote script
  ```
- An explicit, idempotent provisioning step — a `scripts/promote_admin.py` invoked by a
  Makefile target (`make promote-admin`) — sets `role = ADMIN` on the accounts whose
  email is in the allowlist. The **role lives in the DB**; the request path checks only
  the stored role, never the allowlist. Re-running is a no-op.

This keeps production code free of environment branches and makes "who is an admin" an
auditable DB fact.

### 4.4 Security & privacy (the part that needs the most care)

- **Cross-tenant reads are a deliberate exception to ADR-0003** (strict per-business
  isolation). Exactly one role may do it, only for aggregates, read-only. Per §14, this
  is recorded as a new **ADR-0012: the admin role and cross-tenant analytics** before
  code lands — it is a systemic decision, not a local one.
- **Aggregates, not PII.** The admin repository returns counts, sums, and per-business
  rollups — never message bodies, customer addresses, or intake answers. This is enforced
  at the **port boundary**: the admin Protocol's return DTOs simply have no field that can
  carry PII. There is no admin endpoint that returns a `MessageView`/transcript.
- **Rate limiting & audit.** Admin endpoints sit behind the existing `RateLimiter` and
  log access at INFO with the admin account id and the endpoint — **no customer PII**,
  consistent with the June-2026 hardening (PII at DEBUG only).
- **Same-origin cookie + credentialed CORS** already in place; admin endpoints add no new
  auth transport.

---

## 5. Architecture — where the code lives (hexagonal)

Additive only; the core is untouched. Arrows point inward (§9.1).

```
interface/admin_api.py   ──calls──▶  application/analytics.py  ──depends on──▶  ports (Protocols)
  (driving adapter,                    (use case: PlatformAnalytics)                 ▲
   admin guard, Pydantic views)                                                      │
                                                                       infrastructure/postgres
                                                                       SqlPlatform*Repository
                                                                       (GROUP BY in SQL)
```

### 5.1 Ports (Protocols) — segregated, not one God-Protocol (§3.4)

Three cohesive read-ports rather than one with 6+ methods:

```python
# application/ports.py
class PlatformSummaryRepository(Protocol):
    async def totals(self, now: datetime) -> PlatformTotals: ...
    async def activation_funnel(self) -> ActivationFunnel: ...

class PlatformTimeseriesRepository(Protocol):
    async def daily(self, metric: TimeseriesMetric, window: DateWindow) -> list[DailyCount]: ...

class BusinessDirectoryRepository(Protocol):
    async def page(self, query: DirectoryQuery) -> tuple[list[BusinessSummary], int]: ...
```

`TimeseriesMetric` is a `StrEnum` (`SIGNUPS | BOOKINGS | REPLIES | NEW_CUSTOMERS |
LLM_USAGE`). The SQL adapter resolves it through a **registry** `dict[TimeseriesMetric,
QueryFragment]` — adding a metric is a new registry entry, not an edited `if/elif`
(OCP §3.2). The DTOs (`PlatformTotals`, `ActivationFunnel`, `DailyCount`,
`BusinessSummary`, `DateWindow`, `DirectoryQuery`) are **frozen dataclasses** in a new
`application/analytics_models.py` (read models, not domain core — they hold no business
invariants, only shaped numbers).

### 5.2 Use case (application)

```python
# application/analytics.py
class PlatformAnalytics:
    """Assemble the operator overview from the read-ports. Pure orchestration;
    derived rates (no-show %, funnel %) are computed here, not in SQL or the UI."""
    def __init__(self, summary, timeseries, directory, clock): ...
    async def overview(self) -> Overview: ...
    async def timeseries(self, metric: TimeseriesMetric, window: DateWindow) -> list[DailyCount]: ...
    async def businesses(self, query: DirectoryQuery) -> tuple[list[BusinessSummary], int]: ...
```

Derived metrics (no-show rate, cancellation rate, funnel conversion %) live here — they
are business logic, unit-tested against an in-memory fake repository, deterministic via
the injected `Clock`.

### 5.3 Adapter (infrastructure)

`SqlPlatformSummaryRepository`, `SqlPlatformTimeseriesRepository`,
`SqlBusinessDirectoryRepository` in `infrastructure/postgres/adapters.py`. Each does its
aggregation in **one SQL statement** (`count`, `GROUP BY date_trunc('day', ...)`, a single
`JOIN ... GROUP BY business.id` for the directory) — no N+1, no loading rows into Python.
Integration-tested against a real Postgres (Testcontainers, §10.4).

In-memory fakes (`InMemoryPlatformAnalytics...`) back the unit tests for the use case and
the API — real Protocol implementations over in-memory lists, not `Mock` (§6.1.7).

### 5.4 Interface (driving adapter)

```python
# interface/admin_api.py
def build_admin_router(analytics: PlatformAnalytics, guard: Guard) -> APIRouter:
    router = APIRouter(prefix="/api/admin", dependencies=[Depends(guard)])
    # GET /api/admin/overview              -> OverviewView
    # GET /api/admin/timeseries?metric&from&to -> list[DailyCountView]
    # GET /api/admin/businesses?limit&offset&sort&q -> BusinessPageView
    ...
```

Pydantic `BaseModel` views at the boundary (§2.3), ISO-8601 UTC datetimes, server-capped
page sizes (reuse the `_DEFAULT_PAGE_SIZE` / `_MAX_PAGE_SIZE` pattern from `read_api.py`).

### 5.5 Exposing the role to the client

The frontend needs to know the caller is an admin to show the Admin nav. Add a single
source of truth:

```
GET /api/me  ->  { email, business_id | null, role }   # read from the session cookie
```

Cleaner than threading `role` through the OAuth callback URL. `AuthView` may also carry
`role` on login/signup for immediacy. The frontend stores it but **never relies on it for
security** — the admin endpoints' guard is the real gate.

### 5.6 DI wiring (app.py)

In `create_production_app`, build the three Sql repositories + `PlatformAnalytics`, build
`admin_guard = make_admin_guard(accounts, session_signing_key(...), token_max_age)`, and
`app.include_router(build_admin_router(analytics, admin_guard))`. Same assembly style as
every other router; no globals (§6.1.3).

---

## 6. Frontend — the admin area (Next.js dashboard)

Grounded in the current app (Next 16.2.9, React 19, client-rendered, Tailwind v4, strict
CSP, i18n in `app/lib/i18n.ts`, nav in `components/nav-items.ts`, SVG icons in
`components/icons.tsx`).

### 6.1 Role-gated entry

- Extend the `Session` shape (`app/lib/session.ts`) and the login/`/api/me` flow with
  `role`. Show the **Admin** nav item only when `role === "admin"`.
- New route `app/admin/page.tsx` (gets the Sidebar/Topbar shell automatically). It follows
  the established `getSession()` → `loading | anon | ready` pattern; on a non-admin it
  renders an empty state. Real enforcement is server-side (the admin guard returns 403);
  the client gate is only UX.
- Nav: append `{ href: "/admin", key: "nav.admin", icon: "admin" }` to `NAV_ITEMS`, add
  the `admin` icon to the `IconName` union + `PATHS`, add the title to `Topbar`'s `TITLES`.
  Filter the admin item out for non-admins.

### 6.2 Screens

1. **Overview** — KPI cards (the §2.1 headline numbers) + the activation funnel + the four
   primary trend charts (signups, agent replies, bookings, managed LLM usage).
2. **Businesses** — the server-paginated, sortable, searchable directory table (§2.4),
   reusing the calendar page's pagination/search UX.

### 6.3 Charts library

None is installed today. Adding one is required.

- **Recommendation:** **Recharts** — SVG-rendered (themeable via `currentColor` and our
  Tailwind tokens, accessible, no `eval`, so it satisfies the strict CSP
  `script-src 'self' 'nonce' 'strict-dynamic'`; `style-src` already allows
  `'unsafe-inline'`). Satisfies §7.12 (SVG, not emojis/canvas glyphs).
- **§7.10 is mandatory before adding it:** web-search the current stable version of the
  chosen library and pin it; do **not** copy a version from memory. Confirm React-19
  compatibility and that it pulls in no `eval`-using transitive dep that the CSP would
  block. If Recharts fails either check, fall back to **visx** (low-level SVG primitives,
  zero runtime-eval) and compose the few charts we need by hand.
- Charts read their data from the admin API and render client-side, consistent with the
  rest of the app. UTC → local formatting only at render, via the existing `format.ts` /
  `Intl` (§7.7).

### 6.4 i18n, theming, icons

- Every new string added to **all four** locale blocks in `app/lib/i18n.ts` (`en` is the
  type source + fallback) — `nav.admin`, `admin.*` keys (§7.8). No inline literals in JSX.
- Colors via the semantic Tailwind tokens (`bg-surface`, `text-ink`, `bg-accent-soft`,
  …), so charts theme with light/dark automatically.
- Icons via the SVG registry; **no emojis anywhere** (§7.12).

### 6.5 API client

Add typed methods to the `api` object in `app/lib/api.ts` (`adminOverview`,
`adminTimeseries`, `adminBusinesses`, `me`) over the existing `request()` helper
(`credentials: "include"` already sends the cookie). CSP `connect-src` already allows
`NEXT_PUBLIC_API_URL`.

---

## 7. API surface (summary)

| Method & path | Returns | Guard |
|---|---|---|
| `GET /api/me` | `{ email, business_id?, role }` | session (any) |
| `GET /api/admin/overview` | KPI totals + funnel | admin |
| `GET /api/admin/timeseries?metric&from&to` | `[{ day, count }]` | admin |
| `GET /api/admin/businesses?limit&offset&sort&q` | `{ items, total }` | admin |

All admin endpoints: read-only, aggregate-only, rate-limited, access logged without PII.

---

## 8. Testing plan (the coverage gate is a merge condition — §10)

- **Domain/application:** `UserRole` enum and `Account.role` — unit, ≥90%.
- **Application:** `PlatformAnalytics` use case against in-memory fake repositories —
  totals, derived rates (no-show/cancellation %), funnel %, empty-data and
  single-business edge cases. Deterministic via `FrozenClock`. ≥90% incl. error paths.
- **Infrastructure:** the three `Sql*` repositories against real Postgres
  (Testcontainers) — correct GROUP BY buckets across day boundaries (UTC), pagination,
  sorting, the directory JOIN counts. Migrations: "upgrade from clean DB" passes (§10.4).
- **Interface:** `admin_api` via integration tests — **the admin guard rejects an owner
  token (403) and a missing/expired token (401), and accepts an admin token**; shapes
  validate. This is the security-critical test and is explicit.
- **Frontend:** Vitest component tests for the admin pages (loading / anon / non-admin /
  ready states, the nav item hidden for owners), chart components render with sample data.
  A Playwright e2e: admin signs in → sees overview; owner signs in → no Admin nav, `/admin`
  is blocked.
- **Guardrail:** no `datetime.now()`/`random` in tests; in-memory fakes, not mocks;
  coverage must not drop.

---

## 9. Phased delivery (each phase a green-gate, deployable slice)

- **Phase 1 — role + core metrics.** `UserRole` + `account.role` + admin guard + promote
  script; the `created_at` migrations; the summary/timeseries/directory ports + SQL
  adapters + use case; `admin_api`; the Overview + Businesses screens with the §2.1–2.4
  metrics and four charts. ADR-0012 recorded. Full gate green.
- **Phase 2 — funnel depth & event analytics.** Persist domain events (an append-only
  `analytics_event` table written by a **new `EventListener`** — OCP, no use-case edits)
  to unlock escalation counts, reschedule/cancel timelines, and time-to-first-booking
  without re-deriving from entity tables. Cohort/retention views.
- **Phase 3 — operability.** Approval-queue depth & reminder health across tenants;
  export (CSV); date-range presets; optional per-business drill-down **behind a separate
  PII/audit decision** (not assumed).

---

## 10. ADRs to record before code lands

- **ADR-0012 — Admin role & cross-tenant analytics.** Why one read-only role may cross the
  ADR-0003 tenant boundary; the aggregate-only/no-PII constraint; out-of-band
  provisioning; the trade-offs. Required by §14 (this is a systemic decision).

---

## 11. Open questions

- **Charts lib:** Recharts vs visx — settle after the §7.10 version + CSP/eval check.
- **Per-day timezone:** bucket time-series by **UTC day** (simple, operator-facing) vs each
  business's local day. UTC for v1; note it in the API.
- **`/api/me` vs role-in-`AuthView`:** ship `/api/me` as the single source of truth; decide
  whether to also embed `role` in login for first-paint speed.
- **Active-business definition:** "≥1 message in 30d" vs "≥1 booking in 30d" — pick one and
  label it in the UI so the number is unambiguous.
