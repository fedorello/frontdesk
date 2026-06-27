"""The booking use cases and the reminder worker."""

from datetime import timedelta

from frontdesk.application.ports import AppointmentBooked, AppointmentCancelled
from frontdesk.application.worker import SendDueReminders
from frontdesk.domain.enums import AppointmentStatus, Channel, ReminderStatus
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import TimeSlot
from tests.application.world import NOW, build_world, make_customer


def _future_slot(hours: int) -> TimeSlot:
    start = NOW + timedelta(hours=hours)
    return TimeSlot(start, start + timedelta(minutes=60))


async def test_book_schedules_two_reminders_and_publishes() -> None:
    world = build_world([])
    appointment = await world.book(
        world.service, ResourceId("res"), make_customer(), _future_slot(26)
    )

    assert appointment.status == AppointmentStatus.CONFIRMED  # auto-confirmed by default
    assert len(world.reminders.reminders) == 2  # 24h + 2h, both in the future
    assert any(isinstance(event, AppointmentBooked) for event in world.events.events)


async def test_cancel_cancels_reminders_and_publishes() -> None:
    world = build_world([])
    appointment = await world.book(
        world.service, ResourceId("res"), make_customer(), _future_slot(26)
    )

    cancelled = await world.cancel(appointment.id)

    assert cancelled.status == AppointmentStatus.CANCELLED
    assert all(r.status == ReminderStatus.CANCELLED for r in world.reminders.reminders.values())
    assert any(isinstance(event, AppointmentCancelled) for event in world.events.events)


async def test_reschedule_moves_and_refreshes_reminders() -> None:
    world = build_world([])
    appointment = await world.book(
        world.service, ResourceId("res"), make_customer(), _future_slot(26)
    )

    later = _future_slot(28)
    moved = await world.reschedule(appointment.id, later)

    assert moved.slot == later
    pending = [r for r in world.reminders.reminders.values() if r.status == ReminderStatus.PENDING]
    assert len(pending) == 2  # the old two cancelled, two fresh ones scheduled


async def test_send_due_reminders_delivers_and_marks_sent() -> None:
    world = build_world([])
    customer = await world.customers.upsert(BusinessId("biz"), Channel.WHATSAPP, "+CUST")
    appointment = await world.book(world.service, ResourceId("res"), customer, _future_slot(26))

    worker = SendDueReminders(
        world.reminders, world.appointments, world.customers, world.services, world.messaging
    )
    sent = await worker(NOW + timedelta(hours=3))  # the 24h reminder (due NOW+2h) is now due

    assert sent == 1
    assert world.messaging.sent[-1][1].buttons == ("Confirm", "Reschedule")
    assert any(r.status == ReminderStatus.SENT for r in world.reminders.reminders.values())
    assert appointment.status == AppointmentStatus.CONFIRMED  # auto-confirmed by default
