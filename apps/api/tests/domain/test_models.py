"""Value-object and entity validation, plus TimeSlot geometry."""

from datetime import UTC, datetime, time

import pytest

from frontdesk.domain.ids import BusinessId, ResourceId, ServiceId
from frontdesk.domain.models import Business, Resource, Service, TimeSlot, WorkingHours


def _slot(start_hour: int, end_hour: int) -> TimeSlot:
    day = datetime(2026, 6, 26, tzinfo=UTC)
    return TimeSlot(day.replace(hour=start_hour), day.replace(hour=end_hour))


def test_timeslot_duration() -> None:
    assert _slot(9, 10).duration_minutes == 60
    assert _slot(9, 11).duration_minutes == 120


def test_timeslot_overlap_is_half_open() -> None:
    nine_to_ten = _slot(9, 10)
    assert nine_to_ten.overlaps(_slot(9, 10))
    assert nine_to_ten.overlaps(
        TimeSlot(
            datetime(2026, 6, 26, 9, 30, tzinfo=UTC),
            datetime(2026, 6, 26, 10, 30, tzinfo=UTC),
        )
    )
    assert not nine_to_ten.overlaps(_slot(10, 11))  # touching does not overlap


def test_timeslot_rejects_non_positive_range() -> None:
    with pytest.raises(ValueError, match="after"):
        TimeSlot(datetime(2026, 6, 26, 10, tzinfo=UTC), datetime(2026, 6, 26, 9, tzinfo=UTC))


@pytest.mark.parametrize(
    ("weekday", "opens", "closes"),
    [(7, time(9), time(17)), (-1, time(9), time(17)), (0, time(17), time(9))],
)
def test_working_hours_invalid(weekday: int, opens: time, closes: time) -> None:
    with pytest.raises(ValueError, match=r"weekday|after"):
        WorkingHours(weekday, opens, closes)


def test_service_valid() -> None:
    service = Service(ServiceId("s"), BusinessId("b"), "Haircut", 45)

    assert service.duration_minutes == 45
    assert service.price is None
    assert service.resource_ids == ()


def test_service_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="duration"):
        Service(ServiceId("s"), BusinessId("b"), "Haircut", 0)


@pytest.mark.parametrize(("lead", "buffer"), [(-1, 0), (0, -1)])
def test_business_rejects_negative_minutes(lead: int, buffer: int) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        Business(BusinessId("b"), "Studio", "UTC", lead_time_minutes=lead, buffer_minutes=buffer)


def test_resource_holds_working_hours() -> None:
    hours = (WorkingHours(0, time(9), time(17)),)
    resource = Resource(ResourceId("r"), BusinessId("b"), "Ana", hours)
    assert resource.working_hours == hours
