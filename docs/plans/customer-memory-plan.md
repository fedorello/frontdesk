# Customer memory — implementation plan

> Status: **planned** (not started). Inside-out build plan for the concept in
> [`docs/design/customer-memory.md`](../design/customer-memory.md), grounded in the current code and
> following [`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md). Same shape as
> [`premium-features-plan.md`](./premium-features-plan.md).

## 1. Goal

Stop asking the LLM to remember the transcript. Keep a **structured, persisted customer profile**;
inject it into every turn as a "what we already know" section; let the assistant **save a fact via a
tool** the moment the caller gives it; and **source booking intake from the profile**. Result: the
assistant asks each intake field at most once, and **remembers a repeat caller** (same phone number).

## 2. What already exists (touch-points)

The feature slots onto real code — read these before starting:

- **Intake model.** `domain/models.py`: `IntakeField(name, description, ask)` (e.g. `name="Birth
  date"`), `IntakeAnswer(name, value)` stored on the appointment, `Service.intake_fields:
  tuple[IntakeField, ...]`. **The field `name` is the natural key** we reuse for profile facts.
- **The assistant loop.** `application/assistant.py`:
  - Tools live in `TOOL_SPECS: tuple[ToolSpec, ...]` and are dispatched via `self._handlers:
    dict[str, ToolHandler]` (`answer_question`, `find_availability`, `book`, …) + `_dispatch`.
  - The system prompt is built by `_system_prompt(...)` (text) and `_voice_system_prompt(...)`
    (voice), each already injecting `_intake_block(services)` and a per-turn
    `await _appointments_block(business, customer)`.
  - `_do_book` receives a free-form `details` object and turns it into `IntakeAnswer`s via
    `_intake_answers(service, details)` before booking.
  - Dependencies are the `AssistantDeps` dataclass (constructor-injected).
- **Customer identity.** `deps.customers.upsert(business_id, channel, address)` resolves the **same
  `Customer` for the same phone number on every call** — cross-call memory comes for free.
- **Persistence pattern.** DDL in `infrastructure/postgres/schema.py` (mirrored by an Alembic
  migration under `alembic/versions/`); adapters in `infrastructure/postgres/adapters.py`; in-memory
  fakes in `infrastructure/memory.py`; the `customer` table already exists (for the FK).
- **Composition.** `interface/app.py::build_assistant_deps` assembles `AssistantDeps`; the voice app
  (`frontdesk-voice`) reuses it. Any new dep is wired here **and** in every test `_deps` helper and
  in `frontdesk-voice` — see risk §7.

## 3. Architecture (hexagonal)

- **Domain** (`domain/customer_memory.py`, pure): `CustomerFact`, `CustomerProfile` with the rules
  (`get`, `missing`, `with_fact`) — no infra imports (§9.2).
- **Port** (`application/ports.py`): `CustomerProfileRepository` — `get` + `upsert_facts` (2 methods,
  ISP-clean). In-memory fake in `memory.py`.
- **Use case** (`application/customer_memory.py`): `RememberCustomer` — validates keys against the
  business's intake fields, upserts facts through the port, logs (PII at DEBUG only).
- **Tool** (`assistant.py`): a `remember_customer` `ToolSpec` + a `_remember` handler registered in
  `_handlers`; a **safe** tool (no approval gate, ADR-0005), like `find_availability`.
- **Prompt** (`assistant.py`): `_known_customer_block(profile, required_names)` injected by both
  `_system_prompt` and `_voice_system_prompt`, next to the appointments block.
- **Adapter** (`infrastructure/postgres/customer_memory.py`): `SqlCustomerProfileRepository`.

### 3.1 Domain shape

```python
@dataclass(frozen=True, slots=True)
class CustomerFact:
    key: str          # an intake field name, e.g. "Birth date", or the universal "name"
    value: str
    updated_at: datetime

@dataclass(frozen=True, slots=True)
class CustomerProfile:
    customer_id: CustomerId
    business_id: BusinessId
    facts: tuple[CustomerFact, ...]        # one entry per key, latest value

    def value_of(self, key: str) -> str | None: ...
    def missing(self, required: Iterable[str]) -> tuple[str, ...]: ...   # required keys not held
    def with_fact(self, key: str, value: str, now: datetime) -> "CustomerProfile": ...  # upsert
```

Keys are matched **case-insensitively, trimmed** to the intake field names, so "birth date" from the
model maps to the field `"Birth date"` (a small normalization rule, unit-tested).

### 3.2 The `remember_customer` tool

```
remember_customer(details: {<field name>: <value>, ...})
```

- Handler `_remember` → `RememberCustomer.execute(business, customer, details)`.
- Validation: each key must be a known intake field of one of the business's services, or the
  universal `"name"`; unknown keys are dropped (logged), so the profile stays clean — reuse the same
  matching used by `_intake_answers`.
- Idempotent upsert (latest value wins). Returns a short confirmation string for the tool result.

### 3.3 The prompt section

Injected every turn, after the appointments block:

```
What we already know about this caller — use these, never ask for them again:
- name: Theodore
- Birth date: 21 December 1984
- Birth place: Novosibirsk
Still needed for a personal reading: Birth time
```

`_known_customer_block` takes the loaded profile and the required intake names for the offered
services and renders "known" + "still needed". The existing "ask only the next MISSING item"
instruction now has real data to read.

## 4. Data model & migration

```sql
CREATE TABLE customer_fact (
    business_id text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
    customer_id text NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
    key         text NOT NULL,
    value       text NOT NULL,
    updated_at  timestamptz NOT NULL,   -- tz-aware UTC (§7.7)
    PRIMARY KEY (business_id, customer_id, key)
);
```

Added to `schema.py::CREATE_STATEMENTS` (+ its `DROP_STATEMENTS`) and a new Alembic migration
(`00NN_customer_fact.py`, `CREATE TABLE IF NOT EXISTS`, schema-only §12). PII-bearing → follows §7.8
and is removed by the existing account-deletion cascade.

## 5. Assistant wiring (the delicate part)

1. `AssistantDeps` gains `profiles: CustomerProfileRepository`.
2. At the start of a turn (`handle` and `stream`), load the profile once:
   `profile = await self._d.profiles.get(business.id, customer.id)` and pass it into the prompt
   builder alongside `appointments`.
3. `_do_book`: before booking, **merge** the profile's facts into the `details` (profile is the
   source of truth; any freshly-passed detail is also saved). This is how a returning caller books
   without re-stating their birth date.
4. Keep `_known_customer_block` ≤30 lines; extract a `_render_facts` helper if needed (§2.2).

## 6. Inside-out phased plan

Each phase: full local gate green (`ruff`, `mypy --strict`, `import-linter`, `pytest ≥90%`),
Conventional Commits, and — for the phases the voice app consumes — a tagged `frontdesk` release +
re-pin in `frontdesk-voice`.

### Phase 1 — Domain + port + fake (no behavior change)
- `domain/customer_memory.py` (`CustomerFact`, `CustomerProfile` + `value_of`/`missing`/`with_fact`
  + the key-normalization rule).
- `CustomerProfileRepository` port + `InMemoryCustomerProfileRepository` fake.
- **Tests:** domain rules (missing/upsert/normalization) + fake round-trip. ≥90%.

### Phase 2 — Persistence
- `customer_fact` DDL (schema + migration) + `SqlCustomerProfileRepository`.
- **Tests:** real-Postgres integration (save/get, upsert overwrites, cascade delete).

### Phase 3 — Use case + tool
- `RememberCustomer` (validate against intake fields + `"name"`, upsert, DEBUG-log).
- `remember_customer` `ToolSpec` + `_remember` handler in `_handlers`; wire `profiles` into
  `AssistantDeps` + `build_assistant_deps` + every test `_deps` + `frontdesk-voice`.
- **Tests:** use case (valid/unknown keys, idempotent), and an assistant-loop test that a stated
  fact triggers `remember_customer` and is persisted.

### Phase 4 — Prompt + booking integration
- `_known_customer_block` injected in `_system_prompt` + `_voice_system_prompt`; load the profile per
  turn; tighten the instruction to "ask only a Still-needed field; on an answer call
  remember_customer".
- `_do_book` merges profile facts into `details`.
- **Tests:** prompt contains known facts + still-needed; booking sources intake from the profile; a
  golden voice-eval (§10.6) showing each field asked **at most once** across a two-call scenario.
- Tag `frontdesk`, re-pin + redeploy `frontdesk-voice`, verify on a real call.

### Phase 5 — (later) dashboard view
- Owner sees/edits a customer's stored facts (a `GET`/`PUT` under the owner guard + a small UI). Own
  issue; out of scope for the first cut.

## 7. Risks & mitigations

- **`AssistantDeps` fan-out.** A new required field touches every construction site (app, tests,
  voice). Mitigation: add it in one commit (Phase 3), lean on `mypy --strict` to find every site;
  consider a test factory helper to build `AssistantDeps` so future fields touch one place.
- **Prompt bloat / latency.** The known-facts block adds tokens each turn. Mitigation: render only
  non-empty facts + the still-needed list; it replaces transcript re-reading, so net context is
  smaller.
- **Wrong/garbled facts saved.** STT mishears a birth date. Mitigation: read booking-critical facts
  back once before trusting (design §11); keep only the latest value (upsert) so a correction fixes
  it.
- **Cross-tenant leakage.** Facts are strictly `(business_id, customer_id)`-scoped and never joined
  across businesses (ADR-0003), enforced at the port + PK.

## 8. Non-goals (this plan)

- Freeform notes / preferences ("likes mornings") — structured intake facts only.
- Fact history / audit trail — latest value only.
- A customer-facing consent/retention UI — flagged for GA in the design doc, not built here.
