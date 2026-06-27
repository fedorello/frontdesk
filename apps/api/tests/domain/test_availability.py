"""Free-slot computation and booking validation, including timezone handling."""

from datetime import UTC, datetime, time, timedelta

import pytest

from frontdesk.domain.availability import ensure_bookable, free_slots
from frontdesk.domain.errors import LeadTimeViolation, SlotUnavailable
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import Business, Resource, TimeSlot, WorkingHours


def _business(*, tz: str = "UTC", lead: int = 60, buffer: int = 0) -> Business:
    return Business(BusinessId("b"), "Studio", tz, lead_time_minutes=lead, buffer_minutes=buffer)


def _resource(*, opens: int = 9, closes: int = 17, hours: bool = True) -> Resource:
    working = (
        tuple(WorkingHours(day, time(opens), time(closes)) for day in range(7)) if hours else ()
    )
    return Resource(ResourceId("r"), BusinessId("b"), "Ana", working)


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 26, hour, minute, tzinfo=UTC)  # a Friday


def test_free_slots_from_window_start() -> None:
    now, around = _at(8), _at(8)

    slots = free_slots(
        business=_business(),
        working_hours=_resource().working_hours,
        busy=[],
        duration_minutes=60,
        now=now,
        around=around,
    )

    assert len(slots) == 5  # the default limit
    assert slots[0].starts_at == _at(9)  # earliest = now + 60min lead
    assert slots[1].starts_at == _at(9, 15)  # 15-minute step


def test_free_slots_align_to_step_grid() -> None:
    slots = free_slots(
        business=_business(lead=0),
        working_hours=_resource().working_hours,
        busy=[],
        duration_minutes=60,
        now=_at(8),
        around=_at(9, 7),  # mid-window → first candidate aligns to the next 15-min step
        limit=1,
    )

    assert slots[0].starts_at == _at(9, 15)


def test_free_slots_skip_busy_and_buffer() -> None:
    busy = [TimeSlot(_at(9), _at(10))]

    no_buffer = free_slots(
        business=_business(),
        working_hours=_resource().working_hours,
        busy=busy,
        duration_minutes=60,
        now=_at(8),
        around=_at(8),
        limit=1,
    )
    assert no_buffer[0].starts_at == _at(10)  # 09:00 taken; 10:00 is free (half-open)

    with_buffer = free_slots(
        business=_business(buffer=30),
        working_hours=_resource().working_hours,
        busy=busy,
        duration_minutes=60,
        now=_at(8),
        around=_at(8),
        limit=1,
    )
    assert with_buffer[0].starts_at == _at(10, 30)  # 30-min buffer pushes it later


def test_free_slots_respects_lead_time() -> None:
    slots = free_slots(
        business=_business(lead=120),
        working_hours=_resource().working_hours,
        busy=[],
        duration_minutes=60,
        now=_at(8),
        around=_at(8),
        limit=1,
    )

    assert slots[0].starts_at == _at(10)  # now + 2h


def test_free_slots_empty_without_working_hours() -> None:
    slots = free_slots(
        business=_business(),
        working_hours=_resource(hours=False).working_hours,
        busy=[],
        duration_minutes=60,
        now=_at(8),
        around=_at(8),
    )

    assert slots == []


def test_free_slots_converts_business_timezone() -> None:
    # Montevideo is UTC-3: 09:00 local opening is 12:00 UTC.
    slots = free_slots(
        business=_business(tz="America/Montevideo", lead=0),
        working_hours=_resource().working_hours,
        busy=[],
        duration_minutes=60,
        now=_at(0),
        around=_at(0),
        limit=1,
    )

    assert slots[0].starts_at == _at(12)


def test_ensure_bookable_accepts_a_valid_slot() -> None:
    ensure_bookable(
        business=_business(),
        working_hours=_resource().working_hours,
        busy=[],
        slot=TimeSlot(_at(11), _at(12)),
        now=_at(8),
        max_advance_days=30,
    )


def test_ensure_bookable_rejects_inside_lead_time() -> None:
    with pytest.raises(LeadTimeViolation):
        ensure_bookable(
            business=_business(lead=60),
            working_hours=_resource().working_hours,
            busy=[],
            slot=TimeSlot(_at(8, 30), _at(9, 30)),
            now=_at(8),
            max_advance_days=30,
        )


def test_ensure_bookable_rejects_outside_working_hours() -> None:
    with pytest.raises(SlotUnavailable, match="working hours"):
        ensure_bookable(
            business=_business(),
            working_hours=_resource().working_hours,
            busy=[],
            slot=TimeSlot(_at(18), _at(19)),  # after 17:00 close
            now=_at(8),
            max_advance_days=30,
        )


def test_ensure_bookable_rejects_taken_slot() -> None:
    with pytest.raises(SlotUnavailable, match="overlaps"):
        ensure_bookable(
            business=_business(buffer=15),
            working_hours=_resource().working_hours,
            busy=[TimeSlot(_at(11), _at(12))],
            slot=TimeSlot(_at(12), _at(13)),  # within the 15-min buffer of 11-12
            now=_at(8),
            max_advance_days=30,
        )


def test_free_slots_across_multiple_days() -> None:
    # A short window that's fully busy today should yield tomorrow's slot.
    hours = tuple(WorkingHours(day, time(9), time(10)) for day in range(7))
    slots = free_slots(
        business=_business(lead=0),
        working_hours=hours,
        busy=[TimeSlot(_at(9), _at(10))],  # today's only slot is taken
        duration_minutes=60,
        now=_at(8),
        around=_at(8),
        limit=1,
    )

    assert slots[0].starts_at == _at(9) + timedelta(days=1)


def test_free_slots_respects_the_booking_horizon() -> None:
    hours = tuple(WorkingHours(day, time(9), time(17)) for day in range(7))
    # Asking around 10 days out, but the service horizon is only 3 days → nothing offered.
    slots = free_slots(
        business=_business(lead=0),
        working_hours=hours,
        busy=[],
        duration_minutes=60,
        now=_at(8),
        around=_at(9) + timedelta(days=10),
        max_advance_days=3,
        limit=5,
    )

    assert slots == []  # beyond the booking horizon


def test_ensure_bookable_rejects_beyond_horizon() -> None:
    with pytest.raises(SlotUnavailable, match="horizon"):
        ensure_bookable(
            business=_business(lead=0),
            working_hours=_resource().working_hours,
            busy=[],
            slot=TimeSlot(_at(9) + timedelta(days=10), _at(10) + timedelta(days=10)),
            now=_at(8),
            max_advance_days=7,
        )
