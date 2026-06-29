# Admin Dashboard — Implementation Plan

A phased, reviewed build of the admin role + cross-tenant operator analytics dashboard.
The design is in [`docs/design/admin-dashboard.md`](../design/admin-dashboard.md); this is
the **execution order**.

The order is **inside-out** (the repo's convention): ADR first, then the pure
enum/DTOs, then ports + in-memory fakes, then the use case tested against fakes, then the
real edges (migrations, SQL adapters), then auth, then the HTTP interface, then the
frontend. **Every phase ends green against the full gate** in
[`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md) (`make check`: ruff + mypy --strict +
import-linter + pytest + coverage) and is a **self-contained, deployable slice**. One
logical change per commit (§13.3); every commit is Conventional Commits.

## Status

| Phase | Title | Status |
| ----- | ----- | ------ |
| 0 | ADR & contract update | ✅ Done |
| 1 | Role & analytics DTOs (enum + read models) | ✅ Done |
| 2 | Ports & in-memory fakes | ✅ Done |
| 3 | `PlatformAnalytics` use case (against fakes) | ✅ Done |
| 4 | Persistence (migrations + SQL adapters) | ✅ Done |
| 5 | Admin auth (guard, provisioning, `/api/me`) | ✅ Done |
| 6 | Admin HTTP API + DI wiring | ✅ Done |
| 7 | Frontend admin area | ✅ Done |
| 8 | Event analytics (funnel depth) — later | ⬜ Deferred |

Each phase below lists: **Goal · Steps (files) · Tests · Definition of Done · Commit(s).**
Coverage targets follow §10.1 (≥90% in each touched layer).

## Implementation notes (as built)

Phases 0–7 are implemented; three deliberate deviations from the plan, each justified:

1. **Analytics ports are verified per-adapter, not via the shared write-through
   `port_contracts` suite.** Those ports are read-only, so they cannot be seeded through
   their own interface. The in-memory fakes are unit-tested
   (`tests/infrastructure/test_analytics_memory.py`) and the SQL adapters
   integration-tested on real Postgres (`tests/integration/test_postgres_analytics.py`)
   against the same behaviors.
2. **Charts are a small dependency-free inline-SVG component, not a library.** For simple
   daily-count trends a hand-rolled SVG (`components/ui/TrendChart.tsx`) is CSP-safe (no
   `eval`), themeable, and avoids a new dependency (KISS / §7.10) — the design doc allowed
   this SVG fallback.
3. **Playwright e2e + axe (Phase 7) are not yet run** — they need browser binaries and a
   running full stack. Coverage is by component tests (role gating, rendering), the Next
   build, and backend checks (the live app returns 401 on `/api/admin` without a token).
   E2e is a follow-up, not faked.

`created_at` is a persistence-only column (DB `DEFAULT now()`, like `approval.created_at`),
not a domain-model field — see design §3.

---

## Phase 0 — ADR & contract update

**Goal:** record the one systemic decision before any code — admitting a single role that
reads **across** the tenant boundary set by ADR-0003 (required by §14).

**Steps**
- `docs/adr/0012-admin-role-and-cross-tenant-analytics.md` — Status: Accepted. Which rule
  is bent (ADR-0003 strict isolation), why aggregate-only/no-PII makes it safe, out-of-band
  provisioning, the read-only constraint, consequences.
- Update `docs/design/contracts.md` (the canonical contract): the `UserRole` enum, the
  `account.role` column + `CHECK`, the three new `created_at` columns, the analytics ports.
- Update the doc indexes (`docs/README.md`, `CLAUDE.md`) — already list the design doc; add
  this plan + the ADR line.

**Tests:** none (docs only — §10.7).

**DoD:** ADR-0012 accepted and linked from `docs/README.md`; `contracts.md` reflects the
new types; no code changed.

**Commit:** `docs(adr): record the admin role and cross-tenant analytics (ADR-0012)`

---

## Phase 1 — Role & analytics read models

**Goal:** the pure value types, no I/O — so later layers compile against real names.

**Steps**
- `domain/enums.py` — add `class UserRole(StrEnum): OWNER = "owner"; ADMIN = "admin"`.
- `application/ports.py` — `Account` gains `role: UserRole = UserRole.OWNER` (default keeps
  every existing construction site valid; `business_id` is already nullable for admins).
- `application/analytics_models.py` (new) — frozen, slotted dataclasses (read models, no
  invariants beyond shape): `DateWindow` (UTC `start`/`end`), `DailyCount` (`day: date`,
  `count: int`), `PlatformTotals`, `ActivationFunnel`, `BusinessSummary`, `DirectoryQuery`
  (limit/offset/sort/search), `DirectorySort` (`StrEnum`), and `TimeseriesMetric`
  (`StrEnum`: `SIGNUPS | BOOKINGS | REPLIES | NEW_CUSTOMERS | LLM_USAGE`).

**Tests** (`tests/domain/`, `tests/application/`)
- `UserRole` membership; `Account` defaults to `OWNER`; an admin `Account` with
  `business_id=None`, `role=ADMIN` constructs.
- DTO construction + frozen/slots behavior; `DateWindow` rejects an inverted range if we
  add that invariant.

**DoD:** unit coverage ≥90% on the new types; `domain/` imports nothing from the stack;
import-linter green; mypy --strict + ruff clean.

**Commits**
- `feat(domain): add UserRole enum`
- `feat(analytics): add platform analytics read models`

---

## Phase 2 — Ports & in-memory fakes

**Goal:** the seams the use case plugs into — segregated Protocols (ISP §3.4), each backed
by an in-memory fake (not mocks, §6.1.7).

**Steps**
- `application/ports.py` — three cohesive read-ports:
  - `PlatformSummaryRepository`: `totals(now) -> PlatformTotals`, `activation_funnel() -> ActivationFunnel`.
  - `PlatformTimeseriesRepository`: `daily(metric, window) -> list[DailyCount]`.
  - `BusinessDirectoryRepository`: `page(query) -> tuple[list[BusinessSummary], int]`.
- `tests/` fakes — `InMemoryPlatformSummary`, `InMemoryPlatformTimeseries`,
  `InMemoryBusinessDirectory`: real Protocol implementations over in-memory lists, seeded
  from simple fixtures, deterministic via the fixed `Clock`.
- Extend the existing **port-contract** suite (`tests/port_contracts.py`) so any adapter
  (fake now, SQL in Phase 4) must satisfy the same behavioral contract.

**Tests:** the fakes pass the port-contract suite; empty-data and single-business cases.

**DoD:** Protocols have ≤4 methods each (ISP); fakes green on the contract suite; ≥90%.

**Commit:** `feat(analytics): add platform analytics ports and in-memory fakes`

---

## Phase 3 — `PlatformAnalytics` use case

**Goal:** the application behavior — assembly + derived metrics — tested **entirely against
fakes** (no DB, no network).

**Steps**
- `application/analytics.py` — `class PlatformAnalytics` with constructor injection of the
  three repositories + `Clock`. Methods: `overview() -> Overview`, `timeseries(metric,
  window) -> list[DailyCount]`, `businesses(query) -> tuple[list[BusinessSummary], int]`.
- Derived metrics live here (business logic, not SQL/UI): no-show rate, cancellation rate,
  funnel conversion %. Each rate guards division by zero explicitly (returns 0.0 on an empty
  denominator — stated, not a silent `except`).
- Constants for any thresholds/labels in a module-level block (no magic numbers, §7.1).

**Tests** (`tests/application/test_analytics.py`)
- `overview` aggregates the fakes correctly; rates compute (incl. zero-denominator);
  `activation_funnel` percentages; `timeseries` passes the metric through; `businesses`
  paginates/sorts. Deterministic via `FrozenClock`.

**DoD:** ≥90% incl. error/zero paths; no `datetime.now()`/`random` in tests; methods ≤30
lines (§2.2).

**Commit:** `feat(analytics): add PlatformAnalytics use case`

---

## Phase 4 — Persistence (migrations + SQL adapters)

**Goal:** durable, efficient aggregation behind the three ports.

**Steps**
- Alembic migrations (one logical change each; schema-only, no logic — §12):
  - `..._account_role.py` — `account.role text NOT NULL DEFAULT 'owner' CHECK (role IN ('owner','admin'))`.
  - `..._created_at_columns.py` — `created_at timestamptz NOT NULL DEFAULT now()` on
    `account`, `appointment`, `customer` (mirrors the existing `approval.created_at`
    precedent; persistence-only, not on the domain models — see design §3).
  - `..._analytics_indexes.py` — indexes per design §3.1 (`account(created_at)`,
    `appointment(created_at)`, `customer(created_at)`, `message(role, at)`,
    `message(business_id, role)`).
- Mirror every DDL into `infrastructure/postgres/schema.py` so the migration and the
  integration-test schema never drift (the file's stated contract).
- `SqlAccountRepository` reads/writes the new `role` column.
- `infrastructure/postgres/adapters.py` — `SqlPlatformSummaryRepository`,
  `SqlPlatformTimeseriesRepository`, `SqlBusinessDirectoryRepository`. Each aggregates in
  **one SQL statement** (`count`, `GROUP BY date_trunc('day', ...)` in UTC, a single
  `JOIN ... GROUP BY business.id` for the directory) — no N+1, no rows pulled into Python.
- The timeseries adapter resolves `TimeseriesMetric` through a `dict[TimeseriesMetric,
  <query fragment>]` **registry** — adding a metric is a new entry, not an edited `if/elif`
  (OCP §3.2).

**Tests** (`tests/integration/`, real Postgres via the existing harness)
- The SQL adapters pass the same port-contract suite as the fakes (Phase 2).
- Day-bucket correctness **across a UTC day boundary** (insert rows with explicit
  `created_at` either side of midnight UTC); directory pagination/sort/search; the JOIN
  counts; `account.role` round-trips.
- Migration: `upgrade` from a clean DB passes (§10.4); the `CHECK` rejects a bad role.

**DoD:** adapters green on the contract suite + integration tests; migrations apply clean;
import-linter green (adapters may import SQLAlchemy; the use case may not).

**Commits**
- `feat(account): add role column with a check constraint`
- `feat(analytics): add created_at columns and aggregation indexes`
- `feat(analytics): add postgres analytics repositories`

---

## Phase 5 — Admin auth (guard, provisioning, `/api/me`)

**Goal:** authenticate the admin role — reusing the existing token/cookie machinery, no
custom auth (§12).

**Steps**
- `interface/auth.py` — `make_admin_guard(accounts, key, max_age)`: reuses
  `_verified_account`, then requires `account.role is UserRole.ADMIN`. Cross-tenant (no
  path `business_id`). Rejections logged without PII.
- `interface/auth.py` (or a small `me_api.py`) — `GET /api/me` returns `{email,
  business_id, role}` from the session cookie (single source of truth for the client).
  Optionally add `role` to `AuthView` for first-paint.
- `core/settings.py` — `admin_emails: str = ""` (comma-separated; consumed **only** by the
  promote script, never in the request path).
- `scripts/promote_admin.py` + Makefile target `promote-admin` — idempotently set
  `role=ADMIN` for accounts whose email is in `admin_emails`. Uses the DI assembly, the
  injected repo; re-running is a no-op. Logs what it changed.

**Tests** (`tests/interface/`)
- `make_admin_guard`: **rejects an owner token (403)**, rejects a missing/expired/revoked
  token (401), **accepts an admin token** — the security-critical test, explicit.
- `/api/me` returns the right shape for owner vs admin.
- `promote_admin` promotes only allowlisted emails and is idempotent.

**DoD:** guard tests green; promotion is out-of-band and idempotent; no env-branching in
the request path (§7.4); ≥90%.

**Commits**
- `feat(auth): add cross-tenant admin guard and /api/me`
- `feat(admin): add out-of-band admin provisioning script`

---

## Phase 6 — Admin HTTP API + DI wiring

**Goal:** expose the analytics behind the admin guard; wire the graph at the composition
root.

**Steps**
- `interface/admin_api.py` — `build_admin_router(analytics, guard)` with `prefix="/api/admin"`
  and `dependencies=[Depends(guard)]`:
  - `GET /api/admin/overview` → `OverviewView`
  - `GET /api/admin/timeseries?metric&from&to` → `list[DailyCountView]`
  - `GET /api/admin/businesses?limit&offset&sort&q` → `BusinessPageView`
  - Pydantic views at the boundary (§2.3); ISO-8601 UTC; server-capped page size (reuse the
    `_DEFAULT_PAGE_SIZE`/`_MAX_PAGE_SIZE` pattern from `read_api.py`); `metric`/`sort` parsed
    into the enums (invalid value → 422, no magic strings).
- `interface/app.py` — build the three Sql repos + `PlatformAnalytics`, build
  `admin_guard`, `app.include_router(build_admin_router(analytics, admin_guard))`. Apply the
  existing `RateLimiter` to the admin routes. No globals (§6.1.3).

**Tests** (`tests/interface/test_admin_api.py`, integration)
- Each endpoint: admin token → 200 + valid shape; owner/anon → 403/401; bad `metric`/`sort`
  → 422; pagination caps enforced.
- **No-PII assertion:** the response models have no field carrying customer addresses /
  message bodies.

**DoD:** endpoints green; OpenAPI updated automatically (FastAPI); rate-limited; access
logged without PII; ≥90%.

**Commit:** `feat(admin): add cross-tenant analytics endpoints`

---

## Phase 7 — Frontend admin area

**Goal:** the operator UI — role-gated, charted, localized, accessible.

**Steps**
- **Charts dependency (do this first, §7.10):** web-search the current stable version of the
  chosen SVG chart lib (**Recharts** recommended; **visx** fallback), confirm React-19
  compatibility and that it pulls in no `eval`-using dep blocked by the strict CSP, then add
  it pinned to `apps/dashboard/package.json` and update the lock file. SVG only (§7.12).
- `app/lib/session.ts` — `Session` gains optional `role`; `app/lib/api.ts` — add typed
  `me()`, `adminOverview()`, `adminTimeseries()`, `adminBusinesses()` over the existing
  `request()` (`credentials:"include"`).
- Nav gating — append `{ href: "/admin", key: "nav.admin", icon: "admin" }` to
  `components/nav-items.ts`, add the `admin` icon to `components/icons.tsx` (`IconName` +
  `PATHS`), add the title to `Topbar`'s `TITLES`; render the item only when `role === "admin"`.
- Pages — `app/admin/page.tsx` (Overview: KPI cards + funnel + four trend charts) and
  `app/admin/businesses/page.tsx` (the directory table; reuse the calendar page's
  pagination/search UX). Both follow the `loading | anon | ready` pattern; non-admin → empty
  state. Colors via the semantic Tailwind tokens so charts theme with light/dark.
- i18n — add every new key (`nav.admin`, `admin.*`) to **all four** locale blocks in
  `app/lib/i18n.ts` (`en` is the type source + fallback); no inline literals (§7.8).
  UTC→local only at render via `format.ts`/`Intl` (§7.7).

**Tests**
- Vitest components: Overview/Businesses in loading/anon/non-admin/ready states; the Admin
  nav item is hidden for owners; charts render with sample data; an empty-data state.
- Playwright e2e: **admin signs in → sees the overview; owner signs in → no Admin nav and
  `/admin` is blocked.** `axe` a11y check on the admin screens (§10.5).

**DoD:** Vitest + Playwright green; coverage ≥90% on new components incl. empty/error
states; `tsc`/ESLint clean (`--max-warnings=0`, §7.6); no emojis (SVG only).

**Commits**
- `build(dashboard): add the charts library`
- `feat(dashboard): add the role-gated admin area`

---

## Phase 8 — Event analytics (funnel depth) — later

**Goal (deferred):** richer time-series that entity tables can't give — escalations,
reschedule/cancel timelines, time-to-first-booking — without re-deriving from rows.

**Steps (when prioritized)**
- An append-only `analytics_event` table written by a **new `EventListener`** added to the
  existing `DispatchingEventPublisher` — OCP, **no use-case edits** (the events
  `AppointmentBooked`/`Escalated`/… already exist). The listener isolates its own failures
  so persistence never breaks a booking (§8.7).
- New timeseries metrics resolved through the same registry; new admin charts.

**DoD:** event persistence is fire-and-forget-safe; metrics covered ≥90%; a separate ADR
only if the event store changes a public contract.

**Commit (later):** `feat(analytics): persist domain events for funnel analytics`

---

## Cross-cutting gate (every phase)

- `make check` green: ruff (incl. `DTZ` datetime rules), mypy --strict, import-linter,
  pytest, coverage ≥90% on touched layers.
- DI only, constructor-injected; no module-level singletons; in-memory fakes, not mocks.
- No magic numbers/strings (enums + named constants); time only via `Clock`; all datetimes
  tz-aware UTC; secrets/PII never logged at INFO.
- Conventional Commits; one logical change per commit; PR checklist (§11) satisfied.
