"""The reminder worker: a tick sends due reminders; the loop stops on signal."""

import asyncio
from datetime import timedelta

from frontdesk.application.worker import SendDueReminders
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import TimeSlot
from frontdesk.infrastructure.system import FixedClock
from frontdesk.interface.worker import ReminderWorker
from tests.application.world import NOW, World, build_world


def _send(world: World) -> SendDueReminders:
    return SendDueReminders(
        world.reminders, world.appointments, world.customers, world.services, world.messaging
    )


async def test_tick_sends_due_reminders() -> None:
    world = build_world([])
    customer = await world.customers.upsert(BusinessId("biz"), Channel.WHATSAPP, "+CUST")
    start = NOW + timedelta(hours=26)
    await world.book(
        world.service, ResourceId("res"), customer, TimeSlot(start, start + timedelta(minutes=60))
    )
    worker = ReminderWorker(_send(world), FixedClock(NOW + timedelta(hours=3)))

    assert await worker.tick() == 1
    assert world.messaging.sent[-1][1].buttons == ("Confirm", "Reschedule")


async def test_run_until_loops_then_stops() -> None:
    world = build_world([])
    worker = ReminderWorker(_send(world), world.clock, interval_seconds=0.01)
    stop = asyncio.Event()

    task = asyncio.create_task(worker.run_until(stop))
    await asyncio.sleep(0.03)  # let it tick a couple of times
    stop.set()

    await asyncio.wait_for(task, timeout=1)
    assert task.done()
