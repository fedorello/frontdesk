"""Pure availability math: free slots, and whether a slot is bookable."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import LeadTimeViolation, SlotUnavailable
from .models import Business, TimeSlot, WorkingHours


def _windows_for_day(
    working_hours: Sequence[WorkingHours], day_local: date, tz: ZoneInfo
) -> list[TimeSlot]:
    """The schedule's working windows on ``day_local``, as UTC time ranges."""
    windows: list[TimeSlot] = []
    weekday = day_local.weekday()  # Monday = 0
    for hours in working_hours:
        if hours.weekday != weekday:
            continue
        opens = datetime.combine(day_local, hours.opens, tzinfo=tz).astimezone(UTC)
        closes = datetime.combine(day_local, hours.closes, tzinfo=tz).astimezone(UTC)
        windows.append(TimeSlot(opens, closes))
    return windows


def _conflicts(slot: TimeSlot, busy: Sequence[TimeSlot], buffer_minutes: int) -> bool:
    """True if ``slot`` overlaps any busy range expanded by the buffer on both sides."""
    buffer = timedelta(minutes=buffer_minutes)
    for taken in busy:
        expanded = TimeSlot(taken.starts_at - buffer, taken.ends_at + buffer)
        if slot.overlaps(expanded):
            return True
    return False


def _within_working_hours(
    slot: TimeSlot, working_hours: Sequence[WorkingHours], tz: ZoneInfo
) -> bool:
    """True if ``slot`` fits entirely inside one of the schedule's windows."""
    local_day = slot.starts_at.astimezone(tz).date()
    for window in _windows_for_day(working_hours, local_day, tz):
        if window.starts_at <= slot.starts_at and slot.ends_at <= window.ends_at:
            return True
    return False


def free_slots(
    *,
    business: Business,
    working_hours: Sequence[WorkingHours],
    busy: Sequence[TimeSlot],
    duration_minutes: int,
    now: datetime,
    around: datetime,
    max_advance_days: int = 30,
    step_minutes: int = 15,
    limit: int = 5,
) -> list[TimeSlot]:
    """Free slots of ``duration_minutes``, near ``around``, within the booking horizon.

    Respects ``working_hours`` (the service's schedule), the business buffer between
    appointments, the lead time before now, and ``max_advance_days`` (the furthest a
    customer may book). ``now`` and ``around`` are UTC.
    """
    tz = ZoneInfo(business.timezone)
    earliest = max(around, now + timedelta(minutes=business.lead_time_minutes))
    latest = now + timedelta(days=max_advance_days)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    found: list[TimeSlot] = []
    start_day = earliest.astimezone(tz).date()
    for offset in range(max_advance_days + 1):
        for window in _windows_for_day(working_hours, start_day + timedelta(days=offset), tz):
            candidate = window.starts_at
            if candidate < earliest:
                steps = math.ceil((earliest - window.starts_at) / step)
                candidate = window.starts_at + steps * step
            while candidate + duration <= window.ends_at:
                if candidate > latest:
                    return found  # past the booking horizon — nothing further to offer
                slot = TimeSlot(candidate, candidate + duration)
                if candidate >= earliest and not _conflicts(slot, busy, business.buffer_minutes):
                    found.append(slot)
                    if len(found) >= limit:
                        return found
                candidate += step
    return found


def ensure_bookable(
    *,
    business: Business,
    working_hours: Sequence[WorkingHours],
    busy: Sequence[TimeSlot],
    slot: TimeSlot,
    now: datetime,
    max_advance_days: int,
) -> None:
    """Raise if ``slot`` can't be booked: too soon, too far ahead, off-hours, or taken."""
    if slot.starts_at < now + timedelta(minutes=business.lead_time_minutes):
        raise LeadTimeViolation("slot is inside the lead time")
    if slot.starts_at > now + timedelta(days=max_advance_days):
        raise SlotUnavailable("slot is beyond the booking horizon")
    tz = ZoneInfo(business.timezone)
    if not _within_working_hours(slot, working_hours, tz):
        raise SlotUnavailable("slot is outside working hours")
    if _conflicts(slot, busy, business.buffer_minutes):
        raise SlotUnavailable("slot overlaps an existing appointment")
