"""The reminder worker: a tick sends due reminders; the loop stops on signal."""

import asyncio
from datetime import datetime, timedelta

from frontdesk.application.ports import MessageNotDelivered, OutboundMessage
from frontdesk.application.worker import SendDueReminders
from frontdesk.domain.enums import Channel, ReminderStatus
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import Business, Customer, TimeSlot
from frontdesk.infrastructure.system import FixedClock
from frontdesk.interface.worker import ReminderWorker
from tests.application.world import NOW, World, build_world


def _send(world: World) -> SendDueReminders:
    return SendDueReminders(
        world.reminders,
        world.appointments,
        world.customers,
        world.services,
        world.deps.businesses,
        world.messaging,
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


async def test_reminder_uses_the_studio_language_and_time_zone() -> None:
    world = build_world([])
    customer = await world.customers.upsert(BusinessId("biz"), Channel.WHATSAPP, "+CUST")
    start = NOW + timedelta(hours=26)
    await world.book(
        world.service, ResourceId("res"), customer, TimeSlot(start, start + timedelta(minutes=60))
    )
    # Re-locale the studio to Russian in a non-UTC zone before the reminder fires.
    await world.deps.businesses.upsert(
        Business(BusinessId("biz"), "Студия Аны", "America/Montevideo", locale="ru")
    )

    assert await _send(world)(NOW + timedelta(hours=3)) == 1
    message = world.messaging.sent[-1][1]
    assert message.text.startswith("Напоминание: ваша запись")  # studio's language, not English
    assert "UTC-3" in message.text  # Montevideo offset, not a bare "UTC"
    assert message.buttons == ("Подтвердить", "Перенести")  # buttons localized too


async def test_run_until_loops_then_stops() -> None:
    world = build_world([])
    worker = ReminderWorker(_send(world), world.clock, interval_seconds=0.01)
    stop = asyncio.Event()

    task = asyncio.create_task(worker.run_until(stop))
    await asyncio.sleep(0.03)  # let it tick a couple of times
    stop.set()

    await asyncio.wait_for(task, timeout=1)
    assert task.done()


class _Refusing:
    """Refuses the first customer's messages; delivers everyone else's."""

    def __init__(self, refused_address: str, *, permanent: bool) -> None:
        self._refused = refused_address
        self._permanent = permanent
        self.sent: list[str] = []

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        if customer.channel_address == self._refused:
            raise MessageNotDelivered("telegram 400: chat not found", permanent=self._permanent)
        self.sent.append(customer.channel_address)


async def _book_two(world: World) -> None:
    for address, hours in (("+BAD", 26), ("+GOOD", 27)):
        customer = await world.customers.upsert(BusinessId("biz"), Channel.WHATSAPP, address)
        start = NOW + timedelta(hours=hours)
        await world.book(
            world.service,
            ResourceId("res"),
            customer,
            TimeSlot(start, start + timedelta(minutes=60)),
        )


def _send_via(world: World, messaging: _Refusing) -> SendDueReminders:
    return SendDueReminders(
        world.reminders,
        world.appointments,
        world.customers,
        world.services,
        world.deps.businesses,
        messaging,
    )


def _statuses(world: World) -> list[ReminderStatus]:
    return sorted(r.status for r in world.reminders.reminders.values())


async def test_a_permanent_refusal_marks_that_reminder_failed_and_the_rest_still_go() -> None:
    world = build_world([])
    await _book_two(world)
    messaging = _Refusing("+BAD", permanent=True)

    sent = await _send_via(world, messaging)(NOW + timedelta(hours=4))

    assert sent == 1
    assert messaging.sent == ["+GOOD"]
    assert ReminderStatus.FAILED in _statuses(world)
    assert ReminderStatus.SENT in _statuses(world)


async def test_a_temporary_refusal_leaves_the_reminder_pending_for_the_next_pass() -> None:
    world = build_world([])
    await _book_two(world)
    messaging = _Refusing("+BAD", permanent=False)
    send = _send_via(world, messaging)

    await send(NOW + timedelta(hours=4))

    assert ReminderStatus.FAILED not in _statuses(world)
    assert len(await world.reminders.claim_due(NOW + timedelta(hours=4))) == 1  # retried later


async def test_a_reminder_for_an_appointment_that_already_started_is_skipped() -> None:
    world = build_world([])
    customer = await world.customers.upsert(BusinessId("biz"), Channel.WHATSAPP, "+CUST")
    start = NOW + timedelta(hours=26)
    await world.book(
        world.service, ResourceId("res"), customer, TimeSlot(start, start + timedelta(minutes=60))
    )

    sent = await _send(world)(start + timedelta(minutes=5))

    assert sent == 0
    assert world.messaging.sent == []
    assert set(_statuses(world)) == {ReminderStatus.SKIPPED}


class _Exploding:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, now: datetime) -> int:
        self.calls += 1
        raise RuntimeError("database down")


async def test_run_until_keeps_going_after_a_failed_pass() -> None:
    world = build_world([])
    exploding = _Exploding()
    worker = ReminderWorker(exploding, world.clock, interval_seconds=0.01)  # type: ignore[arg-type]
    stop = asyncio.Event()

    task = asyncio.create_task(worker.run_until(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1)

    assert exploding.calls >= 2
