"""RememberCustomer use case + the remember_customer tool end-to-end through the assistant."""

from datetime import UTC, datetime

from frontdesk.application.customer_memory import RememberCustomer
from frontdesk.application.ports import Completion, FactNormalizer, ToolCall
from frontdesk.domain.customer_memory import CustomerFact
from frontdesk.domain.ids import BusinessId, CustomerId, ServiceId
from frontdesk.domain.models import IntakeAnswer, IntakeField, Service
from frontdesk.infrastructure.memory import (
    InMemoryCustomerProfileRepository,
    InMemoryServiceRepository,
)
from frontdesk.infrastructure.providers.groq import NullFactNormalizer
from frontdesk.infrastructure.system import FixedClock
from tests.application.world import build_world, make_customer

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
BIZ = BusinessId("biz")
CUST = CustomerId("cust")


def _remember(
    normalizer: FactNormalizer | None = None,
) -> tuple[RememberCustomer, InMemoryCustomerProfileRepository]:
    service = Service(
        ServiceId("svc"),
        BIZ,
        "Reading",
        60,
        intake_fields=(
            IntakeField("Birth date", normalize="Format as DD.MM.YYYY"),
            IntakeField("Birth time"),
        ),
    )
    profiles = InMemoryCustomerProfileRepository()
    use_case = RememberCustomer(
        profiles,
        InMemoryServiceRepository([service]),
        FixedClock(NOW),
        normalizer or NullFactNormalizer(),
    )
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


class _UppercaseNormalizer:
    """A stub normalizer that uppercases, so a test can prove cleaning is applied before saving."""

    async def normalize(self, field: str, value: str, instruction: str = "") -> str:
        return value.upper()


class _RecordingNormalizer:
    """Records the (field, instruction) it was called with, so a test can assert the per-field
    normalization rule is forwarded from the intake field to the normalizer."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def normalize(self, field: str, value: str, instruction: str = "") -> str:
        self.calls.append((field, instruction))
        return value


async def test_field_normalization_rule_is_forwarded_to_the_normalizer() -> None:
    normalizer = _RecordingNormalizer()
    use_case, _ = _remember(normalizer)

    await use_case.execute(BIZ, CUST, {"Birth date": "21 december", "name": "Theo"})

    # "Birth date" carries the owner's rule; the universal "name" has none.
    assert ("Birth date", "Format as DD.MM.YYYY") in normalizer.calls
    assert ("name", "") in normalizer.calls


async def test_values_are_cleaned_by_the_normalizer_before_saving() -> None:
    use_case, profiles = _remember(_UppercaseNormalizer())

    await use_case.execute(BIZ, CUST, {"Birth date": "21 december"})

    assert (await profiles.get(BIZ, CUST)).value_of("Birth date") == "21 DECEMBER"


async def test_skips_unknown_keys_and_empty_values() -> None:
    use_case, profiles = _remember()

    saved = await use_case.execute(BIZ, CUST, {"favourite colour": "blue", "Birth time": "  "})

    assert saved == ()  # unknown field dropped, blank value dropped
    assert (await profiles.get(BIZ, CUST)).facts == ()


async def test_a_stated_fact_is_captured_even_when_the_reply_skips_remember() -> None:
    # The forced extraction pass runs first and saves the fact; the main reply (2nd completion)
    # calls no tool — proving saving is deterministic, not left to the model's discretion.
    world = build_world(
        [
            Completion(
                None,
                (ToolCall("r", "remember_customer", {"details": {"birth date": "21 Dec 1984"}}),),
            ),
            Completion("Thanks, noted."),  # the reply turn does NOT call remember_customer
        ],
        intake_fields=(IntakeField("Birth date"),),
    )
    customer = make_customer()

    _ = [line async for line in world.assistant.stream(world.business, customer)]

    profile = await world.deps.profiles.get(world.business.id, customer.id)
    assert profile.value_of("Birth date") == "21 Dec 1984"  # captured by the forced pass


async def test_booking_sources_intake_from_the_saved_profile() -> None:
    # A returning caller whose profile already holds the required intake books without re-stating
    # it: the book call passes no details, yet it succeeds because _do_book merges the profile.
    world = build_world(
        [
            Completion(
                "Booking now.",
                (
                    ToolCall(
                        "b", "book", {"service": "Haircut", "start": "2026-06-26T15:00:00+00:00"}
                    ),
                ),
            ),
            Completion("All set."),
        ],
        intake_fields=(IntakeField("Birth date"),),
    )
    customer = make_customer()
    await world.deps.profiles.upsert_facts(
        world.business.id, customer.id, [CustomerFact("Birth date", "21 December 1984", NOW)]
    )

    _ = [line async for line in world.assistant.stream(world.business, customer)]

    assert len(world.appointments.appointments) == 1  # booked despite no details in the tool call
    (booked,) = world.appointments.appointments.values()
    assert booked.intake == (IntakeAnswer("Birth date", "21 December 1984"),)  # from the profile
