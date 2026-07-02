"""Save the facts a customer states into their profile.

Backs the ``remember_customer`` tool. Only keys that match one of the business's intake fields (or
the universal ``name``) are stored, canonicalized to the field's exact spelling, so the profile
stays clean and lines up with what booking expects. Fact *values* are PII and logged only at DEBUG.
"""

import logging
from collections.abc import Mapping

from frontdesk.application.ports import Clock, CustomerProfileRepository, ServiceRepository
from frontdesk.domain.customer_memory import NAME_KEY, CustomerFact, normalize_key
from frontdesk.domain.ids import BusinessId, CustomerId

_logger = logging.getLogger("frontdesk.customer_memory")


class RememberCustomer:
    """Persist the customer's stated intake facts, keyed by the business's intake field names."""

    def __init__(
        self,
        profiles: CustomerProfileRepository,
        services: ServiceRepository,
        clock: Clock,
    ) -> None:
        self._profiles = profiles
        self._services = services
        self._clock = clock

    async def execute(
        self, business_id: BusinessId, customer_id: CustomerId, details: Mapping[str, object]
    ) -> tuple[str, ...]:
        """Save each recognised, non-empty detail. Returns the canonical keys actually saved.

        Unknown keys (not an intake field of any service, and not ``name``) and empty values are
        skipped — so a stray tool argument can never pollute the profile.
        """
        allowed = await self._allowed_keys(business_id)
        now = self._clock.now()
        facts: list[CustomerFact] = []
        for raw_key, raw_value in details.items():
            canonical = allowed.get(normalize_key(raw_key))
            value = str(raw_value).strip()
            if canonical is not None and value:
                facts.append(CustomerFact(canonical, value, now))
        if facts:
            await self._profiles.upsert_facts(business_id, customer_id, facts)
        saved = tuple(fact.key for fact in facts)
        # Keys only — values are PII (§7.8).
        _logger.info("customer_facts_saved business=%s keys=%s", business_id, list(saved))
        return saved

    async def _allowed_keys(self, business_id: BusinessId) -> dict[str, str]:
        """Normalized key -> canonical name, for ``name`` plus every service's intake fields."""
        keys = {normalize_key(NAME_KEY): NAME_KEY}
        for service in await self._services.for_business(business_id):
            for field in service.intake_fields:
                keys[normalize_key(field.name)] = field.name
        return keys
