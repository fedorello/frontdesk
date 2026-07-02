"""CustomerProfile rules + the in-memory profile fake."""

from datetime import UTC, datetime

from frontdesk.domain.customer_memory import CustomerFact, CustomerProfile, normalize_key
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.infrastructure.memory import InMemoryCustomerProfileRepository

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 3, 9, 0, tzinfo=UTC)
BIZ = BusinessId("biz")
CUST = CustomerId("cust")


def _profile(*facts: CustomerFact) -> CustomerProfile:
    return CustomerProfile(CUST, BIZ, facts)


def test_normalize_key_folds_case_and_trims() -> None:
    assert normalize_key(" Birth Date ") == normalize_key("birth date")


def test_value_of_matches_case_insensitively() -> None:
    profile = _profile(CustomerFact("Birth date", "21 December 1984", NOW))

    assert profile.value_of("birth date") == "21 December 1984"
    assert profile.value_of("Birth time") is None


def test_missing_returns_unheld_required_keys_keeping_their_spelling() -> None:
    profile = _profile(CustomerFact("birth date", "x", NOW))

    assert profile.missing(["Birth date", "Birth time", "Birth place"]) == (
        "Birth time",
        "Birth place",
    )  # the held one is dropped; the others keep their display spelling


def test_with_fact_upserts_matching_keys_and_keeps_the_latest_value() -> None:
    profile = _profile(CustomerFact("Birth time", "16:00", NOW))

    updated = profile.with_fact("birth time", "18:30", LATER)  # same key, different case

    assert len(updated.facts) == 1  # no duplicate key
    assert updated.value_of("Birth time") == "18:30"
    assert updated.facts[0].updated_at == LATER


async def test_fake_repository_round_trips_and_overwrites() -> None:
    repo = InMemoryCustomerProfileRepository()

    assert (await repo.get(BIZ, CUST)).facts == ()  # empty profile before anything is stored

    await repo.upsert_facts(BIZ, CUST, [CustomerFact("Birth date", "21 Dec 1984", NOW)])
    await repo.upsert_facts(BIZ, CUST, [CustomerFact("birth date", "1 Jan 1990", LATER)])

    profile = await repo.get(BIZ, CUST)
    assert len(profile.facts) == 1  # upsert overwrote, not appended
    assert profile.value_of("Birth date") == "1 Jan 1990"
