"""Real-Postgres round-trips for the customer-memory adapter."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.customer_memory import CustomerFact
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.infrastructure.postgres.customer_memory import SqlCustomerProfileRepository

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 3, 9, 0, tzinfo=UTC)
BIZ = BusinessId("biz")  # seeded by the integration conftest
CUST = CustomerId("cus")


async def test_upsert_then_get_round_trips(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlCustomerProfileRepository(sessionmaker)

    await repo.upsert_facts(
        BIZ,
        CUST,
        [CustomerFact("Birth date", "21 December 1984", NOW), CustomerFact("name", "T", NOW)],
    )
    profile = await repo.get(BIZ, CUST)

    assert profile.value_of("Birth date") == "21 December 1984"
    assert profile.value_of("name") == "T"
    assert len(profile.facts) == 2


async def test_upsert_overwrites_the_same_key(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlCustomerProfileRepository(sessionmaker)

    await repo.upsert_facts(BIZ, CUST, [CustomerFact("Birth time", "16:00", NOW)])
    await repo.upsert_facts(BIZ, CUST, [CustomerFact("Birth time", "18:30", LATER)])

    profile = await repo.get(BIZ, CUST)
    assert len(profile.facts) == 1  # overwrote in place
    assert profile.value_of("Birth time") == "18:30"


async def test_get_is_empty_for_a_customer_with_no_facts(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    profile = await SqlCustomerProfileRepository(sessionmaker).get(BIZ, CustomerId("nobody"))

    assert profile.facts == ()
