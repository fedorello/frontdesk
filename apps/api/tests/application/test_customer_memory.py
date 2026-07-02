"""RememberCustomer use case + the remember_customer tool end-to-end through the assistant."""

from datetime import UTC, datetime

from frontdesk.application.customer_memory import RememberCustomer
from frontdesk.application.ports import Completion, ToolCall
from frontdesk.domain.ids import BusinessId, CustomerId, ServiceId
from frontdesk.domain.models import IntakeField, Service
from frontdesk.infrastructure.memory import (
    InMemoryCustomerProfileRepository,
    InMemoryServiceRepository,
)
from frontdesk.infrastructure.system import FixedClock
from tests.application.world import build_world, make_customer

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
BIZ = BusinessId("biz")
CUST = CustomerId("cust")


def _remember() -> tuple[RememberCustomer, InMemoryCustomerProfileRepository]:
    service = Service(
        ServiceId("svc"),
        BIZ,
        "Reading",
        60,
        intake_fields=(IntakeField("Birth date"), IntakeField("Birth time")),
    )
    profiles = InMemoryCustomerProfileRepository()
    use_case = RememberCustomer(profiles, InMemoryServiceRepository([service]), FixedClock(NOW))
    return use_case, profiles


async def test_saves_recognised_intake_fields_and_the_universal_name() -> None:
    use_case, profiles = _remember()

    saved = await use_case.execute(
        BIZ, CUST, {"birth date": "21 December 1984", "name": "Theodore"}
    )

    assert set(saved) == {"Birth date", "name"}  # canonicalized to the field's exact spelling
    profile = await profiles.get(BIZ, CUST)
    assert profile.value_of("Birth date") == "21 December 1984"
    assert profile.value_of("name") == "Theodore"


async def test_skips_unknown_keys_and_empty_values() -> None:
    use_case, profiles = _remember()

    saved = await use_case.execute(BIZ, CUST, {"favourite colour": "blue", "Birth time": "  "})

    assert saved == ()  # unknown field dropped, blank value dropped
    assert (await profiles.get(BIZ, CUST)).facts == ()


async def test_remember_customer_tool_persists_a_fact_through_the_assistant() -> None:
    world = build_world(
        [
            Completion(
                "One moment.",
                (ToolCall("r", "remember_customer", {"details": {"birth date": "21 Dec 1984"}}),),
            ),
            Completion("Thanks, noted."),
        ],
        intake_fields=(IntakeField("Birth date"),),
    )
    customer = make_customer()

    _ = [line async for line in world.assistant.stream(world.business, customer)]

    profile = await world.deps.profiles.get(world.business.id, customer.id)
    assert profile.value_of("Birth date") == "21 Dec 1984"  # tool → use case → persisted
