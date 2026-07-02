"""Postgres adapter for customer memory — remembered facts per customer.

Mirrors the session/text-query style of ``adapters.py``. Keys are the business's intake field names
(canonicalized by the use case before saving), so the primary-key upsert overwrites in place.
"""

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.customer_memory import CustomerFact, CustomerProfile
from frontdesk.domain.ids import BusinessId, CustomerId


class SqlCustomerProfileRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def get(self, business_id: BusinessId, customer_id: CustomerId) -> CustomerProfile:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT key, value, updated_at FROM customer_fact "
                            "WHERE business_id = :b AND customer_id = :c ORDER BY key"
                        ),
                        {"b": str(business_id), "c": str(customer_id)},
                    )
                )
                .mappings()
                .all()
            )
        facts = tuple(CustomerFact(row["key"], row["value"], row["updated_at"]) for row in rows)
        return CustomerProfile(customer_id, business_id, facts)

    async def upsert_facts(
        self, business_id: BusinessId, customer_id: CustomerId, facts: Sequence[CustomerFact]
    ) -> None:
        async with self._sf() as session:
            for fact in facts:
                await session.execute(
                    text(
                        "INSERT INTO customer_fact (business_id, customer_id, key, value, "
                        "updated_at) VALUES (:b, :c, :k, :v, :at) "
                        "ON CONFLICT (business_id, customer_id, key) DO UPDATE SET "
                        "value = :v, updated_at = :at"
                    ),
                    {
                        "b": str(business_id),
                        "c": str(customer_id),
                        "k": fact.key,
                        "v": fact.value,
                        "at": fact.updated_at,
                    },
                )
            await session.commit()
