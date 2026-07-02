# Customer memory — a persistent structured profile injected into every turn

> Status: **concept** (design, not yet implemented). Feature design in the style of
> [`admin-dashboard.md`](./admin-dashboard.md), following
> [`CODING_PRINCIPLES.md`](../../CODING_PRINCIPLES.md) and the hexagon in
> [`architecture/overview.md`](../architecture/overview.md).

## 1. Problem

Today the assistant is expected to *remember* everything a customer says by re-reading the raw
conversation transcript. On voice calls with a weak, fast model this fails badly: it re-asks a
detail the caller already gave ("what time were you born?" three times), loops back to a question it
already answered, and loses track across a multi-field intake. It also forgets everything the moment
the call ends — a repeat caller starts from zero.

The root cause is architectural, not "the model is dumb": **we are asking the LLM to be the memory.**
An LLM is unreliable at bookkeeping over a long transcript, and the transcript is thrown away between
sessions.

## 2. The idea

**Don't make the model remember — give it the facts.** Keep a **structured customer profile**: the
things we've learned about a customer (name, and the business's intake fields — e.g. an astrologer's
date of birth, birth time, birthplace). Two moving parts:

1. **A save tool.** When the caller states a fact, the assistant calls a tool to persist it to the
   customer's profile, instead of only replying.
2. **A "what we already know" prompt section.** Every turn, we inject the customer's current profile
   into the system prompt in its own section. The model reads facts instead of reconstructing them.

Because the profile is **persisted per customer** (keyed by their channel address — their phone
number for voice), it also survives the call: **a repeat caller is remembered** — "Welcome back,
Theodore. Still booking a personal reading?"

The assistant then asks **only for the required intake fields that are still missing**, never
re-asking what the profile already holds.

## 3. Why this is the right fix

- **Correctness over recall (CODING_PRINCIPLES §1).** State lives in a store we control, not in the
  model's attention. The model's only job is to converse and to call the save tool — both things
  LLMs do well.
- **Model-agnostic.** Works with the fast voice model *and* a smarter one; it removes the dependency
  on the model's memory entirely.
- **Cross-channel.** The same profile is shared by voice, Telegram, and WhatsApp for the same
  customer, so context follows the customer across channels.
- **Extensible.** New fact types are data (a business's intake fields), not code.

## 4. Domain model (pure)

```python
@dataclass(frozen=True, slots=True)
class CustomerFact:
    key: str          # a stable field name, e.g. "date_of_birth" or "name"
    value: str        # the captured value, as the customer gave it
    updated_at: datetime

@dataclass(frozen=True, slots=True)
class CustomerProfile:
    customer_id: CustomerId
    business_id: BusinessId
    facts: tuple[CustomerFact, ...]   # latest value per key

    def get(self, key: str) -> str | None: ...
    def missing(self, required: Iterable[str]) -> tuple[str, ...]:  # required keys we don't hold yet
        ...
    def with_fact(self, key: str, value: str, now: datetime) -> "CustomerProfile":  # upsert one key
        ...
```

Keys are the business's **intake field names** (already modelled on `Service.intake_fields`) plus a
small set of universal keys (`name`). Facts are per `(business_id, customer_id)` — strictly
tenant-scoped (ADR-0003), never shared across businesses.

## 5. The save tool (assistant tool)

A new tool the model can call, alongside `find_availability`/`book`:

```
remember_customer(details: {<field_name>: <value>, ...})
```

- **When:** the moment the caller states a required detail — the model calls `remember_customer`
  with just that field, then continues the conversation.
- **Effect:** the use case upserts the fact(s) into the profile via `CustomerProfileRepository`, so
  the *next* turn's prompt already contains them.
- **Validation:** unknown field names (not an intake field of any offered service, and not a
  universal key) are rejected by the domain, so the profile stays clean.
- **Idempotent:** re-saving the same field overwrites, keeping the latest value.

This is a **safe, non-money tool** — it runs automatically (no approval gate, ADR-0005), like
`find_availability`.

## 6. The prompt section

Injected every turn, next to the existing appointments block (`_appointments_block`), a new
`_known_customer_block(profile)`:

```
What we already know about this caller (do NOT ask for any of these again — use them):
- name: Theodore
- date_of_birth: 21 December 1984
- birthplace: Novosibirsk
Still missing for a personal reading: birth_time
```

The prompt instruction becomes: *"Ask only for a field under 'Still missing'. When the caller gives
one, call remember_customer to save it. Never ask for anything already listed above."* This turns
intake from "remember the transcript" into "read the checklist".

## 7. Persistence

A new table, tenant-scoped and PII-bearing (so it follows §7.8 and the account-deletion cascade):

```sql
CREATE TABLE customer_fact (
    business_id text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
    customer_id text NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
    key         text NOT NULL,
    value       text NOT NULL,
    updated_at  timestamptz NOT NULL,
    PRIMARY KEY (business_id, customer_id, key)
);
```

One row per fact (upsert on the PK). `CustomerProfileRepository` (a new port) reads the profile for a
customer and upserts facts; an in-memory fake backs the tests. The customer is resolved exactly as
today — `customers.upsert(business_id, channel, address)` — so the **same phone number maps to the
same profile on every call**, giving cross-call memory for free.

## 8. Hexagonal fit

- **Domain:** `CustomerFact`, `CustomerProfile` (pure, with `missing`/`with_fact` rules).
- **Port:** `CustomerProfileRepository` (`get`, `upsert_facts`) + in-memory fake.
- **Use case:** `RememberCustomer` (validate keys against intake fields, upsert). The `Assistant`
  loads the profile at the start of a turn and injects `_known_customer_block`; the `remember_customer`
  tool dispatches to `RememberCustomer`.
- **Adapters:** `SqlCustomerProfileRepository` (Postgres). No change to channels or model providers —
  the feature is entirely in the core + a tool.
- **Booking:** at `book` time, the intake answers are taken from the profile (single source of
  truth) rather than re-parsed from the reply.

## 9. Privacy & data

- Facts are **PII** — logged at DEBUG only (never INFO), deleted with the account (FK cascade), and
  scoped to one tenant.
- A business can see/edit a customer's stored facts in the dashboard (a future addition); the
  customer's right to deletion is honoured via the existing account-deletion path.
- Consider a per-business retention/consent setting before GA (open question §11).

## 10. Phased plan (inside-out)

1. **Domain + port + fake:** `CustomerFact`, `CustomerProfile` (+ `missing`/`with_fact`),
   `CustomerProfileRepository`, in-memory fake. Unit-tested to ≥90%.
2. **Persistence:** `customer_fact` table (schema + migration) + `SqlCustomerProfileRepository` +
   integration test.
3. **Use case + tool:** `RememberCustomer`; register the `remember_customer` tool; validate keys.
4. **Prompt wiring:** load the profile per turn; inject `_known_customer_block`; instruct
   ask-only-missing + save-on-answer. Update the golden agent evals (ADR/§10.6).
5. **Booking integration:** source intake answers from the profile at `book` time.
6. **(Later) dashboard view:** let owners see/edit a customer's stored facts.

Definition of done per phase: full local gate green (ruff, mypy --strict, import-linter, pytest
≥90%), and an eval showing the assistant asks each intake field **at most once** across a two-call
scenario.

## 11. Open questions

- **Universal vs per-service keys:** is `name` universal, and are intake keys namespaced per service
  or shared across a business? (Proposed: shared per business; a key is an intake field of *any* of
  the business's services, plus `name`.)
- **Correction flow:** if a caller says "actually my birth time is 18:30, not 16:00", the model
  calls `remember_customer` again (upsert). Do we keep history? (Proposed: keep only the latest;
  history is out of scope.)
- **Confidence / confirmation:** should the assistant read a saved fact back once ("so, born the
  21st of December — got it") before trusting it? (Proposed: yes for booking-critical fields.)
- **Consent & retention:** per-business retention window and a customer opt-out — before GA.
- **Non-intake memory:** freeform notes ("prefers mornings") — a later, separate concept; this doc
  covers structured intake facts only.
