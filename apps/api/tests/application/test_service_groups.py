"""Service groups: same-group services share one calendar; different groups are independent.

These are the invariants from docs/SERVICE_GROUPS.md — the reason the schedule lives on the
group and not on the service.
"""

from datetime import time

import pytest

from frontdesk.domain.enums import Channel
from frontdesk.domain.errors import DoubleBooking
from frontdesk.domain.ids import BusinessId, CustomerId, ResourceId, ServiceId
from frontdesk.domain.models import Business, Customer, Resource, Service, WorkingHours
from frontdesk.infrastructure.memory import (
    InMemoryAppointmentRepository,
    InMemoryCalendar,
    InMemoryServiceRepository,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from tests.application.world import NOW

_ALL_WEEK = tuple(WorkingHours(day, time(9), time(17)) for day in range(7))
_CUSTOMER = Customer(CustomerId("cus"), BusinessId("biz"), Channel.WHATSAPP, "+1")


def _service(service_id: str, group_id: str) -> Service:
    return Service(
        ServiceId(service_id),
        BusinessId("biz"),
        service_id,
        60,
        resource_ids=(ResourceId(group_id),),
    )


def _calendar(services: list[Service], groups: list[Resource]) -> InMemoryCalendar:
    return InMemoryCalendar(
        Business(BusinessId("biz"), "Studio", "UTC"),
        groups,
        FixedClock(NOW),
        SequentialIdGenerator("ap"),
        InMemoryAppointmentRepository(),
        InMemoryServiceRepository(services),
    )


async def test_same_group_services_share_one_calendar() -> None:
    group = Resource(ResourceId("ana"), BusinessId("biz"), "Ana", _ALL_WEEK)
    consult, reading = _service("consult", "ana"), _service("reading", "ana")
    calendar = _calendar([consult, reading], [group])

    slot = (await calendar.find_availability(consult, NOW))[0]
    await calendar.book(consult, ResourceId("ana"), _CUSTOMER, slot)

    # The other service in the SAME group can't take that slot — it's one specialist.
    with pytest.raises(DoubleBooking):
        await calendar.book(reading, ResourceId("ana"), _CUSTOMER, slot)
    # ...and the slot disappears from the other service's availability too.
    assert all(not s.overlaps(slot) for s in await calendar.find_availability(reading, NOW))


async def test_different_group_services_can_be_booked_in_parallel() -> None:
    ana = Resource(ResourceId("ana"), BusinessId("biz"), "Ana", _ALL_WEEK)
    bob = Resource(ResourceId("bob"), BusinessId("biz"), "Bob", _ALL_WEEK)
    calendar = _calendar([_service("a", "ana"), _service("b", "bob")], [ana, bob])

    slot = (await calendar.find_availability(_service("a", "ana"), NOW))[0]
    await calendar.book(_service("a", "ana"), ResourceId("ana"), _CUSTOMER, slot)

    # Bob is a different specialist — bookable at the SAME time, no DoubleBooking.
    booked = await calendar.book(_service("b", "bob"), ResourceId("bob"), _CUSTOMER, slot)
    assert booked.slot.starts_at == slot.starts_at


async def test_availability_follows_the_groups_schedule() -> None:
    # A Tuesday-only group makes every service in it Tuesday-only (the schedule is the group's).
    group = Resource(
        ResourceId("ana"), BusinessId("biz"), "Ana", (WorkingHours(1, time(10), time(12)),)
    )
    calendar = _calendar([_service("s1", "ana"), _service("s2", "ana")], [group])

    for service_id in ("s1", "s2"):
        slots = await calendar.find_availability(_service(service_id, "ana"), NOW)
        assert slots  # there are slots within the booking horizon
        assert all(slot.starts_at.weekday() == 1 for slot in slots)  # all on Tuesday
