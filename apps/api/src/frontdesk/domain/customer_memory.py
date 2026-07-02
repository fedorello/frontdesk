"""Customer memory — a structured, persisted profile of what we know about a customer.

The assistant reads these facts from the prompt instead of remembering the transcript, and saves a
new fact (via the ``remember_customer`` tool) the moment the caller states one. Keyed by the
business's intake field names (plus the universal ``name``). See docs/design/customer-memory.md.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from frontdesk.domain.ids import BusinessId, CustomerId

NAME_KEY = "name"  # the one universal fact key, present for every business


def normalize_key(key: str) -> str:
    """Fold a fact/field name to its comparison form, so 'Birth date' == 'birth date '."""
    return key.strip().casefold()


@dataclass(frozen=True, slots=True)
class CustomerFact:
    """One thing we know about a customer — an intake field value or their name."""

    key: str  # an intake field name (e.g. "Birth date") or NAME_KEY
    value: str
    updated_at: datetime  # tz-aware UTC


@dataclass(frozen=True, slots=True)
class CustomerProfile:
    """Everything we know about one customer of one business — the latest value per key."""

    customer_id: CustomerId
    business_id: BusinessId
    facts: tuple[CustomerFact, ...] = ()

    def value_of(self, key: str) -> str | None:
        target = normalize_key(key)
        return next((fact.value for fact in self.facts if normalize_key(fact.key) == target), None)

    def missing(self, required: Iterable[str]) -> tuple[str, ...]:
        """The required keys we don't hold yet, keeping each name's spelling for display."""
        held = {normalize_key(fact.key) for fact in self.facts}
        return tuple(name for name in required if normalize_key(name) not in held)

    def with_fact(self, key: str, value: str, now: datetime) -> CustomerProfile:
        """Upsert one fact (latest value wins), matching keys case-insensitively."""
        target = normalize_key(key)
        kept = tuple(fact for fact in self.facts if normalize_key(fact.key) != target)
        return replace(self, facts=(*kept, CustomerFact(key, value, now)))
