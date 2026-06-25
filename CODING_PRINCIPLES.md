# Code Principles & Engineering Rules

> **This document is my personal standard of code quality.** It applies to all my projects without exception. Every line of code, every PR, every architectural decision is checked against this document. If a rule here conflicts with the "convenient" approach — the rule wins.
>
> **Audience:** all developers (including AI assistants), architects, code reviewers.
>
> **Genre:** not "good practices in general", but **enforceable rules for code review**. Every rule is phrased so that it can be applied as a "yes/no" check.

---

## 1. Core Values

In order of priority:

1. **Correctness.** The code does what it claims. Fully. With no hidden limitations.
2. **Testability.** Any piece of code is testable in isolation. No mock magic. **Goal — ≥ 90% coverage in key areas.**
3. **Architectural cleanliness.** SOLID is followed strictly, with no relaxations. DI is a categorical imperative.
4. **Readability.** A new developer understands the code within half a day without explanations.
5. **Extensibility.** A new feature is added without rewriting the existing code.
6. **Performance.** Only after the first five.

When a conflict arises — we choose the option that is higher on the list.

---

## 2. Clean Code — concrete rules

### 2.1. Naming

- **Identifiers are expressive.** `user_orders` is better than `data`. `calculate_total_cost` is better than `calc`.
- **No abbreviations** except commonly accepted ones (HTTP, URL, ID, JSON, API, SQL, UUID). `usr` is forbidden, `user` is mandatory.
- **A verb for functions, a noun for classes.** `place_order()`, not `order_placement()`. `OrderService`, not `OrderManager`.
- **No `Util`, `Helper`, `Manager`, `Handler`, `Processor`.** If a class is named like that — it is poorly specified, split it into concrete ones.
- **Boolean: `is_*`, `has_*`, `should_*`, `can_*`.** `is_available`, not `available`.
- **Constants — UPPER_SNAKE_CASE.** Classes — `PascalCase`. Functions/methods/variables — `snake_case` (Python) or `camelCase` (TS/JS).
- **No `IFoo`-style prefixes for interfaces** — the name is self-sufficient: `Clock`, not `IClock`. If you need to distinguish it from the implementation — use the `Protocol` suffix: `ClockProtocol`.

### 2.2. Sizes

- **Function/method:** ≤ 30 lines (excluding decorators/docstring). More — extract a helper.
- **Class:** ≤ 200 lines. More — the class has several responsibilities, split it.
- **File:** ≤ 3000 lines. More — the module is too general, split it by concepts.
- **Function parameters:** ≤ 4. More — gather them into a parameter object (Pydantic / dataclass / TypeScript interface).
- **Nesting level:** ≤ 3 (if/for/with/try). More — extract a function or use early return.
- **Line length:** ≤ 100 characters.

### 2.3. Types and annotations

- **Python:** type annotations on all public functions/methods/attributes are **mandatory**. `mypy --strict` in CI.
- **TypeScript:** `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`. `any` is forbidden without an explicit comment `// eslint-disable-next-line — reason: ...`.
- **No `Optional[Any]`** without justification. If you don't know the type — design it.
- **Pydantic v2 (Python) / Zod (TS) for all user input + structured data.** No `dict[str, Any]` at API boundaries.
- **Domain types:** for important business entities create dedicated types, do not use raw `str` / `int` (Value Objects, `NewType`, branded types).

### 2.4. Comments

> **⚠️ Categorical imperative: ALL comments and docstrings in the code — ONLY in English, in plain and clear language.** No exceptions. Applies to all projects, all files, all programming languages.

- **Code explains WHAT, comments explain WHY.** No `# increments counter` next to `counter += 1`.
- **A comment is needed if:** there is a hidden constraint, a non-obvious workaround, a reference to an issue, an illogical business rule, a non-intuitive algorithm, an explanation of "why exactly this way and not the obvious one".
- **Delete dead comments.** `# TODO: fix later` with no reference to an issue = delete it or replace it with a proper TODO with an issue (see §8.2).
- **Docstrings are mandatory** for public functions/classes. 1–3 lines. Not a retelling of the code — purpose, edge cases, invariants.
- **In moderation.** Well-named code does not need comments. Don't add comments "because it's supposed to be there".
- **English — plain and clear.** Short phrases. No slang. No jargon that a second developer would not understand.

Examples:

```python
# ✅ Good — explains WHY (a non-obvious constraint).
# Retry only on transient network errors; payload validation errors must surface
# so the caller can fix the request instead of looping forever.
if isinstance(error, TransientNetworkError):
    return self._retry(request)

# ❌ Bad — restates the code.
# Check if error is transient
if isinstance(error, TransientNetworkError):
    return self._retry(request)

# ❌ Bad — Russian / mixed language comment.
# Повторяем только при сетевых ошибках
```

```python
# ✅ Good docstring: purpose + edge cases, not a code retelling.
def place_order(cart: Cart, user: User) -> Order:
    """Create and persist an order from the current cart.

    Raises EmptyCartError if the cart has no items.
    Raises OutOfStockError if any item is no longer available.
    """
```

---

## 3. SOLID — strict adherence

### 3.1. Single Responsibility (SRP)

- A class — one reason to change.
- A method/function — one action, expressed by a verb in its name.
- If the name contains `and` — it is definitely an SRP violation.
- If a class has ≥ 7 public methods — check whether SRP is violated.

### 3.2. Open/Closed (OCP)

- Extension through **new** classes/functions, not through **modifying** existing ones.
- Extension points — via Protocol interfaces + DI.
- **No `if isinstance(x, ConcreteClass)` in business logic** — this is an OCP violation. Use polymorphism.
- **No `if type_key == "...": ... elif type_key == "...":`** for controlling behavior — this is a switch instead of polymorphism. Register variants via a registry/factory.

### 3.3. Liskov Substitution (LSP)

- A subclass / Protocol implementation must work in place of the base without surprises.
- Do not narrow preconditions in subclasses. Do not widen postconditions.
- **`NotImplementedError` in a subclass is forbidden** — if a method is not needed, do not inherit; split the interface (see ISP).
- A subclass must not throw new exception types that are not declared in the base contract.

### 3.4. Interface Segregation (ISP)

- One Protocol — one use case. No "God-Protocol" with 20 methods.
- A client must not depend on methods it does not use.
- If a Protocol has ≥ 5 methods — it almost always should be split into two or more.

### 3.5. Dependency Inversion (DIP)

- **High-level modules do NOT depend on low-level ones.** Both depend on abstractions.
- **Dependencies — via Protocol interfaces.** `PaymentGatewayProtocol`, not `StripeGateway` directly.
- **Injection — via the constructor.** No `from project.gateways.stripe import gateway` inside a service.
- Concrete implementations are wired together only in the DI container at application startup.

---

## 4. DRY — but carefully

- **Knowledge being duplicated is bad.** If the same business logic is in 3 places — extract it.
- **Similar code ≠ a duplicate.** Two places that happen to look alike but represent different concepts — keep them separate.
- **Rule of three:** duplication twice — leave it. From the 3rd time — decide whether to extract the common part.
- **WET (Write Everything Twice) is better than premature abstraction** that will turn out to be wrong in 6 months.
- Before extracting a common part — ask: "Are they really about the same concept?"

---

## 5. KISS

- **Simple working code is better than elegant complex code.**
- **No metaclasses / magic decorators / hidden imports**, if they can be avoided.
- **No clever one-liners.** If a line takes 30 seconds to understand — break it up.
- **Minimum of abstractions.** Every new abstraction must solve a concrete current problem, not a "possible future use case".
- **YAGNI** — don't build generalizations "for the future": you'll add them when they're needed.

---

## 6. Dependency Injection — **categorical imperative**

DI is the foundation of all projects. It is **not an "option" and not a "style" — it is a requirement**. Without DI the code will not pass review.

### 6.1. DI rules (no exceptions)

1. **Any dependency on the outside world — via a Protocol interface.**
   - DB → `XxxRepositoryProtocol`.
   - HTTP API → `XxxGatewayProtocol`.
   - LLM / AI → `LLMProviderProtocol`.
   - Time → `ClockProtocol` (to test `datetime.now()`).
   - Randomness → `RandomProtocol` (so that tests are deterministic).
   - UUID generation → `IdGeneratorProtocol`.
   - File system → `FileSystemProtocol`.
   - Event / message bus → `EventBusProtocol`.
   - Logger (if centralized) → `LoggerProtocol`.

2. **Dependencies are passed ONLY via the constructor.**

   ```python
   # ✅ Correct: dependencies are explicit and injectable.
   class OrderService:
       def __init__(
           self,
           orders: OrderRepoProtocol,
           payments: PaymentGatewayProtocol,
           events: EventBusProtocol,
           clock: ClockProtocol,
       ) -> None:
           self._orders = orders
           self._payments = payments
           self._events = events
           self._clock = clock

   # ❌ Forbidden: hidden, non-testable dependencies.
   class OrderService:
       def __init__(self) -> None:
           self._orders = SqlOrderRepository()  # hard-wired
           self._now = datetime.now()            # non-deterministic
   ```

3. **No global singletons at the module level.**

   ```python
   # ❌ Forbidden:
   engine = create_async_engine(DATABASE_URL)  # global, non-testable

   # ✅ Correct: engine is provided by the DI container as a Singleton.
   ```

4. **No `import` of concrete implementations in the services / use-cases layer.**
   - `from project.gateways.stripe import StripeGateway` inside a service — a DIP violation.
   - `from project.gateways.payment.protocol import PaymentGatewayProtocol` — OK (this is an interface).

5. **One DI container per application.** Works for API + workers + scripts + tests. A single assembly point for the dependency graph.

6. **Tests use override, not monkey-patching:**

   ```python
   # ✅ Correct: container override is refactor-safe.
   with container.payment_gateway.override(FakePaymentGateway()):
       await service.place_order(...)

   # ❌ Forbidden: monkey-patching breaks on rename / move.
   monkeypatch.setattr("project.services.order_service.payment", fake)
   ```

7. **In-memory fakes, not mocks for every method.** Create `FakePaymentGateway`, `InMemoryOrderRepo` — real implementations of a Protocol with in-memory state. They are **far more resilient to refactoring** than `Mock(spec=...)`. A single fake is reused across all tests.

### 6.2. What to always inject via DI

- All clients of external APIs.
- All Repositories (DB access).
- All sources of non-determinism (time, randomness, UUID, system load).
- All sources of configuration (`Settings`).
- All event buses, message queues.
- All LLM / AI providers.
- Loggers, if centralized.
- Any resources with a lifecycle (HTTP sessions, connection pools).

---

## 7. No hardcoding — **categorical imperative**

### 7.1. No magic numbers

```python
# ❌ Forbidden:
if order.total > 800:
    fee = order.total * 0.04

# ✅ Correct:
# In a project-level constants module:
FREE_SHIPPING_THRESHOLD = Decimal("800")
PROCESSING_FEE_RATE = Decimal("0.04")

# In service code:
if order.total > FREE_SHIPPING_THRESHOLD:
    fee = order.total * PROCESSING_FEE_RATE
```

### 7.2. No magic strings

```python
# ❌ Forbidden:
if user.role == "admin": ...

# ✅ Correct:
class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"

if user.role == UserRole.ADMIN: ...
```

### 7.3. Configuration — ONLY via ENV / config files

- **Any setting** = read via `Settings` (Pydantic Settings or equivalent) from ENV / `.env`.
- **No** `os.getenv()` scattered across the code. Only via DI-injected `Settings`.
- **Business parameters** (thresholds, limits, rates) — in a central parameters file, not scattered across the code.
- **LLM configs** (model, temperature, max_tokens) — via config, not hardcoded in agent code.
- **Feature flags** — via a DI-injected `FeatureFlagsProtocol`, not `if os.getenv(...)`.

### 7.4. No environment-specific branches in production code

```python
# ❌ Forbidden:
if os.getenv("ENVIRONMENT") == "production":
    use_real_payment()
else:
    use_fake_payment()

# ✅ Correct:
# DI container injects the right `payment_provider` based on config.
# Service receives PaymentGatewayProtocol and does not know what's inside.
```

### 7.5. No `if testing: ...` in production code

- Tests substitute behavior via DI override, not via runtime checks.
- Production code must not know that it is running in a test.

### 7.6. No warnings, no deprecated code

Any warning from tooling is a merge blocker.

- **Python:** `ruff` warnings, `mypy` warnings, `DeprecationWarning` / `PendingDeprecationWarning` on import or when running tests.
- **TypeScript:** any `tsc` errors. ESLint warnings = errors (`--max-warnings=0`).
- **Node:** stdlib deprecation warnings from the `node` process.
- **Package managers:** errors and warnings in install logs.
- **CSS / Tailwind:** PostCSS warnings.
- **Browser:** console warnings/errors in production = an alert.
- **CI:** a yellow CI = a red CI, it must be fixed.

**What "fixing" a warning means:**

- Update the package version to one that is not deprecated.
- Replace the deprecated API with the current one (`datetime.utcnow()` → `datetime.now(UTC)`).
- Remove the deprecated dependency.
- If a warning is safe and unavoidable (for example, from a third-party library) — `# noqa: WARN_CODE — reason: ...` with an explicit justification and a link to an upstream issue that shows work on a patch.

**Forbidden:**

- Ignoring warnings, hoping to "get to them later".
- Silencing the output (`2>/dev/null`, `--silent`) just to not see it.
- Postponing updates of packages with known deprecation notices.

**Why:** warnings are a backlog of bug reports from tooling. Accumulating warnings = a drop in signal/noise → real problems get lost in the noise. Deprecated code = in one of the next tooling versions the project will break.

### 7.7. Datetime — timezone-aware UTC everywhere

- ✅ **Only** `datetime.now(UTC)` (Python 3.12+: `from datetime import UTC`).
- ❌ `datetime.now()` without an argument — forbidden (yields naive local).
- ❌ `datetime.utcnow()` — deprecated in 3.12+, forbidden.
- ❌ Naive datetimes in models/functions/DB — forbidden.
- ✅ Postgres: all datetime columns `TIMESTAMPTZ` (no `TIMESTAMP WITHOUT TIME ZONE`).
- ✅ SQLAlchemy / ORM: `DateTime(timezone=True)` is mandatory.
- ✅ API JSON: ISO 8601 with offset (`2026-05-14T12:00:00+00:00` or `...Z`). Pydantic v2 does this automatically for aware datetimes.
- ✅ All logs and events — UTC.
- ✅ Current time — only via a `ClockProtocol` injection. `FrozenClock` in tests must throw on an attempt to pass a naive datetime.
- ✅ Frontend converts UTC → user-local **only at render**, via `Intl.DateTimeFormat` with an explicit `locale`.
- ✅ In CI: ruff rules `DTZ001`, `DTZ005`, `DTZ007` are enabled (catches naive datetime usage).

### 7.8. Locale-aware data model from the MVP

Even if the project is single-culture, the data schema and API are designed for multi-locale support from the very start:

- ✅ Backend domain errors carry a `code` + `message_key` (machine-readable), **not already-localized strings**.
- ✅ All content tables with system text — a field `locale TEXT NOT NULL` with a CHECK whitelist of allowed locales.
- ✅ `user.preferred_locale TEXT NOT NULL DEFAULT '<base>'` — added from the first version of the schema.
- ✅ Frontend formatting (dates, numbers, currency) — only via `Intl.*` APIs with an explicit `locale` parameter.
- ✅ User-facing strings — in separate modules/constants, not inline in JSX/templates, ready to be extracted into `messages/<locale>.json`.
- ❌ We do not localize: brand names, product codes, URL slugs, machine-readable error codes.

### 7.9. No hardcoded secrets / endpoints / model IDs

- API keys, tokens, passwords — only via ENV.
- URLs of external services — via `Settings` (production / staging / dev differ).
- Identifiers of LLM models, embedding models, version tags — via config.
- No `https://api.production.example.com` inline in the code.

### 7.10. Only current stable versions of packages

> **⚠️ Categorical imperative.** Before adding **any** dependency (or updating an existing one) you must check the current stable version via web search / the official site / PyPI / npm registry / GitHub releases.

- **Forbidden** to copy `^1.2.3` from an old `pyproject.toml`/`package.json` without checking that it's current.
- **Forbidden** to use LTS/legacy versions if an active stable branch exists and is maintained (for the prod runtime — yes; for developer libraries — the latest stable).
- **Forbidden** to add dependencies without specifying a version (`some-pkg = "*"` or the `latest` Docker image tag) — this kills build reproducibility.
- **Mandatory** to pin versions: exact (`==1.2.3`) for applications, ranges (`~=1.2.3` / `^1.2.3`) for libraries, always with a lock file (`uv.lock` / `pnpm-lock.yaml` / `package-lock.json`).
- **Mandatory** to update the lock file when direct dependencies change.
- **Regularly** run `uv tree --outdated` / `pnpm outdated` / `npm outdated` — outdated >6 months = a planned update.
- **Security:** an SCA scan (Dependabot / `trivy fs`) on every PR. A Critical/High CVE = a merge blocker.
- **Docker base images** — pinned by digest (`@sha256:...`), but the base is updated at least once a quarter.
- **Minor/patch updates** — automatically via Dependabot/Renovate in a separate PR with a CI run.
- **Major updates** — in a separate PR with a review of the changelog, breaking changes, migration steps.

**Why:** old dependencies = a backlog of vulnerabilities + a loss of optimization opportunities + the risk that the next major version drifts so far away that migration becomes very expensive.

**Practical rule for AI assistants:** before generating `pyproject.toml` / `package.json` / Dockerfile — **web search is mandatory** for "<package> latest stable version" or look at PyPI/npm/Docker Hub. Never rely on knowledge from training data for version numbers — they go stale within months.

### 7.11. Python — only `uv` as the package manager

> **⚠️ Categorical imperative.** For all Python projects use **`uv`** — and only it. No `pip install`, `poetry`, `pipenv`, `conda`, `virtualenv` separately.

- **`uv`** — the only supported manager for Python projects. A single tool covers: installing the interpreter (`uv python`), creating a venv, resolving dependencies, the lock file (`uv.lock`), running commands (`uv run`), syncing (`uv sync`).
- `pyproject.toml` — the only source of dependency configuration. `requirements.txt` is not used (only if an external tool requires it — we generate it via `uv export`).
- **No** `pip install <pkg>` inside scripts and CI — only `uv add <pkg>` or `uv pip install`.
- `uv.lock` is committed. Without it the build is not reproducible.
- In Docker: `uv` is installed as the first step, then `uv sync --frozen --no-dev` for the prod stage.
- In CI: `uv sync --frozen` + `uv run <command>` (pytest, ruff, mypy).
- Updating dependencies: `uv lock --upgrade-package <pkg>` for a targeted one, `uv sync --upgrade` for a general bump (always in a separate PR).

**Why:** `uv` is 10–100× faster than pip, has a native lock file, correctly resolves the dependency graph, supports workspaces, and the cache is unified. It is the de facto standard of Python tooling since 2025. Using two managers at the same time (pip + poetry, for example) is the main source of "it works locally but not in CI".

### 7.12. UI icons — only SVG, no emojis

> **⚠️ Categorical imperative.** In the user interface **emojis are forbidden**
> (👤📍✦🕑💡🎉🗑 and any other pictographic symbols). Icons — **only inline SVG**.

- ✅ A single icon component (`Icon.svelte` / `<Icon name="trash" />`) with a set of SVG paths
  that inherit `currentColor` and accept `size`.
- ✅ Icons scale, are recolored by the theme, are accessible (`aria-hidden` / `aria-label`),
  and render identically on all platforms.
- ❌ Emojis render differently across OSes/fonts, break vertical alignment,
  are not controllable by color/size, and look unprofessional.
- ❌ Do not use dingbat glyphs (`✦`, `✎`, `★`) as icons — they have the same problems.
- Text arrows in CTAs (`→`, `←`) are acceptable as typography; icon-based actions
  (delete, edit, status) — always SVG.

**Why:** emojis are font glyphs outside the application's control: different rendering, no unified
size/color, problems with dark theme and accessibility. SVG icons are deterministic and brandable.

---

## 8. No fakes / hacks / sloppiness

### 8.1. If something is not ready — do NOT simulate it behind the scenes

- **Simulation is acceptable only if it is part of the agreed MVP scope** and is **explicitly** marked in the UI (for example, "Place Order (Demo)").
- **Hidden simulation is forbidden.** If a function is declared as "computes X", it really computes it. It does not return a fixed value "because we'll finish it later".

### 8.2. No TODOs without an issue tracker

```python
# ❌ Forbidden:
# TODO: handle this case later
return None

# ✅ Correct: link to a real issue with context.
# TODO(#142): handle empty result. For now, return None — see issue for plan.
return None

# Even better — implement it now and remove the TODO.
```

### 8.3. No empty catch blocks

```python
# ❌ Forbidden:
try:
    do_something()
except Exception:
    pass  # silently swallow the failure

# ✅ Correct:
try:
    do_something()
except SpecificError as exc:
    logger.warning("operation_failed", reason=str(exc))
    # Decide explicitly: retry? default value? propagate?
```

- Never catch `Exception` without logging and an explicit decision.
- Never catch `BaseException` (it includes `KeyboardInterrupt`, `SystemExit`).
- Every `except` — a specific type, with a deliberate handling.

### 8.4. No `Any` without justification

`Any` is an escape hatch. If you use it — a comment next to it explaining "why exactly `Any` cannot be avoided", and a link to an issue if it's planned to be removed.

### 8.5. No partial implementations

If a feature works at 60% — it is **not finished**. Edge cases are **part of the feature**, not a nice-to-have. If an edge case is explicitly moved to the backlog — that's OK, but it must be **in an issue**, not in the code as "we'll get to it later".

### 8.6. No "timeout = 1 hour" on retry

Clear, justified timeout / retry / backoff values. No "I set a large value so it would definitely work". The justification is in a comment or in an architectural decision.

### 8.7. No silent failures

- Every error is either handled, or logged, or propagated. No "swallowed and forgotten".
- Every retry has an upper attempt limit + backoff.
- Every async fire-and-forget has a callback / status / monitor.

---

## 9. Clean architecture — layers

### 9.1. Backend layers (arrows point inward)

```
api/  →  services/  →  domain/   ← (centre, no outward deps)
                              ↑
              gateways/  ──────┘
              repositories/
              workers/
```

- **Domain** knows nothing about HTTP clients, ORM, web frameworks. These are pure types, invariants, value objects, business rules.
- **Services / use-cases** work only with Protocol interfaces from the domain. They contain the orchestration of business logic.
- **Adapters (api/gateways/repositories/workers)** implement the Protocols. This is where `httpx`, ORM, framework-specific code lives.

### 9.2. Forbidden imports (enforced via import-linter or equivalent)

Domain has no right to import:

- ORM (`sqlalchemy`, `prisma`, `tortoise`, etc.).
- HTTP clients (`httpx`, `requests`, `aiohttp`).
- Web frameworks (`fastapi`, `flask`, `django`).
- Caches, queues (`redis`, `kafka-python`, `celery`).
- The file system, env, OS.
- Any `gateways/`, `repositories/`, `api/` modules of the project.

Services have no right to import concrete implementations of gateways / repositories — only their Protocols.

Checked in CI. A violation = a red build.

### 9.3. Frontend feature-based

- `features/<feature>/` — a self-contained module.
- No cross-feature imports except via `shared/`.
- One feature knows nothing about another, except for URL routing.
- A feature's state lives inside the feature (Zustand store / Redux slice / Pinia store / etc.).

### 9.4. Folder structure (recommended, but not dogma)

```
project/
├── domain/           # pure types, value objects, business rules, protocols
├── services/         # use-cases, orchestration
├── api/              # HTTP routers, request/response models
├── gateways/         # external API clients (each behind a protocol)
├── repositories/     # DB access (each behind a protocol)
├── workers/          # background tasks
├── core/
│   ├── settings.py   # Pydantic Settings
│   ├── container.py  # DI container
│   ├── logging.py    # logger setup
│   └── clock.py      # ClockProtocol + RealClock + FrozenClock
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 10. Testing — **mandatory rule**

> Goal: **≥ 90% coverage in key areas.** Coverage is not a wish, but a merge condition.

### 10.1. Coverage targets

- **Domain layer: ≥ 90%** line + branch coverage. These are pure functions and invariants — a key area, covered to the maximum.
- **Services / use-cases: ≥ 90%** including error paths.
- **Repositories / Gateways: ≥ 90%** (some HTTP edge cases are expensive to cover, the rest is mandatory).
- **API endpoints: ≥ 90%** (via integration tests).
- **Frontend components: ≥ 90%** including loading / error / empty states.
- **AI agent tools: ≥ 90%**.
- **AI agent loop / parser: ≥ 90%**.

A coverage gate in CI. A drop in coverage blocks the merge.

### 10.2. Test pyramid

```
       /\
      /  \   E2E — 5–10 critical scenarios
     /----\
    /      \  Integration — repositories, gateways, events
   /--------\
  /          \ Unit — services, domain, tools — 90% of all tests
 /____________\
```

### 10.3. Unit tests — rules

- **Isolation** — no real DBs, HTTP, file system.
- **In-memory fakes** implementing a Protocol. **Not mocks for every method.**
- **One concept per test.** One assert or a group of related ones.
- **Naming:** `test_<method>_<scenario>_<expected>`. Example: `test_place_order_with_empty_cart_raises_error`.
- **Arrange-Act-Assert structure** — visually separated by blank lines.
- **Deterministic.** No `datetime.now()` or `random.randint()` — via `ClockProtocol` / `RandomProtocol`.
- **Fast.** The whole unit suite must run in < 30 seconds.
- **Independent.** Tests do not depend on execution order and do not share state.

### 10.4. Integration tests — rules

- **A real DB via Testcontainers (or equivalent).** Not mocks.
- **Each test — an isolated DB** (via transaction rollback or a per-test schema).
- **They test the adapter ⇄ infrastructure layer.** Not business logic (that's unit).
- **They test migrations** — `migrate up` from a clean DB passes without errors.
- **They test contracts with external APIs** via recorded HTTP responses (VCR fixtures or equivalent).

### 10.5. E2E tests — rules

- **Real-browser automation** (Playwright or equivalent) for all frontend e2e.
- **The full stack** via docker-compose (or equivalent).
- **5–10 critical user journeys** in the MVP. Not 100. Quality > quantity.
- **External services are mocked** in e2e (determinism). Real ones — only in a separate eval suite.
- **Visual regression** for key screens.
- **Accessibility checks** via `axe` — fail on critical violations.

### 10.6. AI eval (if the project has AI agents)

- **Each agent has a golden dataset** of ≥ 30 cases.
- **Run on changes to prompts or model configuration.**
- **Metrics:** tool sequence correctness, final answer relevance, constraint adherence, no hallucination.
- **Pass rate ≥ 90%** for a production agent.
- **A regression blocks the merge** in an agent-relevant PR.

### 10.7. What we do **NOT cover** with tests (smart exclusions)

- Generated code (for example, an OpenAPI client).
- Type definitions without logic.
- The `main.py` entry point (tested via e2e).
- Pure config dictionaries (if they are not computed).
- Migration scripts (tested via integration "upgrade works").

### 10.8. Test principles in one line

- **Test behavior, not implementation.** A test must survive a refactor of the internals.
- **Fakes > Mocks.** An in-memory implementation of a Protocol is better than `Mock(spec=...)`.
- **Reset state between tests.** No global state leaking between tests.
- **No flaky tests.** A flaky test = either fixed immediately, or deleted.

---

## 11. Code Review Checklist

Before merge, every PR is checked for:

### Architecture

- [ ] All dependencies via Protocol + DI?
- [ ] Domain does not import infrastructure?
- [ ] A service does not import a concrete gateway / repository?
- [ ] Magic numbers / strings extracted into named constants / enums?
- [ ] Configuration via Settings / config, not `os.getenv` scattered around?

### Clean code

- [ ] Naming expressive, no abbreviations?
- [ ] Functions ≤ 30 lines? Classes ≤ 200? Files ≤ 3000?
- [ ] Type annotations on all public functions?
- [ ] Comments in English? Explaining WHY, not WHAT?
- [ ] No redundant / dead comments?

### Tests

- [ ] Coverage did not drop?
- [ ] Unit tests on new logic ≥ the required %?
- [ ] Integration tests if adapters are affected?
- [ ] E2E if new user-facing functionality?
- [ ] Deterministic? (no `datetime.now`, `random`, network calls)?
- [ ] In-memory fakes used, not Mock?

### Security

- [ ] Pydantic / Zod validation on input?
- [ ] PII / secrets not logged?
- [ ] Secrets not in code / commits?
- [ ] Rate limiting on new mutating endpoints?

### Documentation

- [ ] OpenAPI updated (for FastAPI / NestJS — automatically)?
- [ ] An architectural decision (ADR) recorded, if the decision is systemic?
- [ ] README / changelog updated, if a breaking change?
- [ ] Commit messages comply with Conventional Commits (§13)? A breaking change marked with `!` / `BREAKING CHANGE`?

---

## 12. Anti-patterns — categorically forbidden

A consolidated list (details in each section above):

- ❌ Global singletons at the module level (`db = create_engine(...)` in an import).
- ❌ Direct import of implementations in `services/`.
- ❌ Direct SQL queries / ORM calls in API routers.
- ❌ Direct `httpx.get()` / `fetch()` in services.
- ❌ Magic numbers / magic strings.
- ❌ `if os.getenv("TESTING")` in production code.
- ❌ `Any` without justification.
- ❌ Empty `except Exception: pass`.
- ❌ Hardcoded LLM models / API keys / endpoints.
- ❌ Mocks for every method (instead of in-memory fakes).
- ❌ Logic in DB migrations (only schema changes).
- ❌ God-services / God-functions / God-Protocols.
- ❌ Custom auth (we use ready, proven libraries).
- ❌ Premature microservice splitting.
- ❌ Optimistic UI without verification of the server response.
- ❌ TODOs without an issue tracker.
- ❌ Naming via abbreviations (`usr`, `mgr`, `util`, `obj`).
- ❌ Emojis in the UI (see §7.12) — only SVG icons.
- ❌ Comments and docstrings not in English.
- ❌ Naive datetime (without timezone).
- ❌ `NotImplementedError` in a leaf subclass.
- ❌ Silencing warnings / deprecation notices.
- ❌ Commits not following Conventional Commits / meaningless messages (`wip`, `fix`, `update`) (§13).

---

## 13. Git and commit messages — **Conventional Commits are mandatory**

> Commit messages are the machine-readable history of the project. They feed changelog auto-generation,
> semantic versioning, and navigation through history. A free form breaks all of this, so the format is a
> **categorical imperative**, checkable as "yes/no" (via commitlint in CI / a git hook).

### 13.1. Format — Conventional Commits 1.0.0

```
<type>(<scope>)<!>: <description>

[optional body]

[optional footer(s)]
```

- **type** (mandatory, lowercase) — one of:
  `feat` (new functionality), `fix` (a bug fix), `docs` (documentation only),
  `test` (tests only), `refactor` (no behavior change), `perf` (performance),
  `build` (build/dependencies), `ci` (CI configuration), `chore` (routine without prod code),
  `style` (formatting), `revert` (reverting a commit).
- **scope** (optional, in parentheses) — the affected area: the name of a crate/module/feature
  (`feat(genome): ...`, `fix(sim): ...`, `docs(gdd): ...`).
- **description** — brief, in the **imperative mood in English**, lowercase, with no
  period at the end, ≤ 72 characters in the header. ("add splice validation", not "added/adds/Added.").
- **body** (optional) — the WHY and context; a line break after the header is mandatory.
- **footer** — `Refs #123` / `Closes #123` to link to an issue; `Co-Authored-By:` when needed.

### 13.2. Breaking changes

- A `!` marker before the `:` (`feat(protocol)!: change wire format`) **and/or** a footer
  `BREAKING CHANGE: <description>`.
- A breaking change in a public contract (API, event format, wire protocol) — is always marked;
  it affects the semver major.

### 13.3. Rules

- **One commit — one logical change.** Do not mix `feat` and an unrelated `refactor`.
- **Header ≤ 72 characters**, body — lines ≤ 100 characters.
- **Language — English** (like all comments, §2.4).
- **Meaningless messages are forbidden:** `wip`, `fix`, `update`, `stuff`, `.`, `asdf` — a merge blocker.
- **The type matches the content:** a commit that only changes tests — `test`, not `feat`.
- **Enforcement:** `commitlint` (config `@commitlint/config-conventional`) + a git hook (`husky`/
  `lefthook` / `pre-commit`) locally, and a check in CI on every PR. A yellow CI = a red one (§7.6).

```
# ✅ Good
feat(genome): surface recessive thermal gene on crossbreed
fix(sim): clamp expressed traits to [0,100] to prevent overflow
docs(gdd): add 09-SHIPS hull/module stat tables
refactor(net)!: switch wire format from JSON to postcard

BREAKING CHANGE: clients older than v0.3 can no longer decode snapshots.

# ❌ Bad
update stuff
fixed bug
WIP
Добавил новую механику        # not English, no type
```

---

## 14. When a rule may be broken

**Never without a public justification.**

If there is a solid reason — it is recorded as an architectural decision record (ADR) with an explanation:

- Which rule we are breaking.
- Why the alternatives are worse (with concrete trade-offs).
- What the consequences are (technical debt, risks).
- When a return to the rule is planned (if applicable) + the review trigger.

"I know better" is not an argument. The argument is a concrete, measurable advantage, agreed with the team.

---

## 15. Applying this document

- **In onboarding:** a new developer reads this document first thing.
- **In code review:** the reviewer cites a specific item when rejecting a PR.
- **In CI:** automated checks (formatter, linter, type-checker, import-linter, coverage gate) enforce what can be enforced by a machine.
- **In AI memory:** this document is saved — all AI-assisted PRs comply with the rules automatically.
- **In new projects:** it is copied into the repository as the first commit, before any code.

The document is living. Every clarification/rule discovered in work is added here via a PR (with a justification in the commit message). Changes that contradict the spirit of the document require an ADR.

---

## 16. TL;DR

> **Clean code, clean architecture, strict SOLID, no hardcoding, no hacks, everything done honestly via DI, everything covered ≥ 90% with tests using in-memory fakes, ALL comments and docstrings — in English, commits following Conventional Commits. Any exception requires an ADR.**
