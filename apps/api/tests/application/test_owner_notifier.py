"""The owner notifier: messages the owner on schedule changes, through their bot, when linked."""

from datetime import UTC, datetime, timedelta

from frontdesk.application.owner_notifier import OwnerNotifier
from frontdesk.application.ports import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentConfirmed,
    AppointmentRescheduled,
)
from frontdesk.domain.enums import AppointmentStatus, Channel
from frontdesk.domain.ids import AppointmentId, BusinessId, ResourceId, ServiceId
from frontdesk.domain.models import Appointment, Business, Service, TimeSlot
from frontdesk.domain.notifications import OwnerTelegramLink
from frontdesk.infrastructure.memory import (
    InMemoryAppointmentRepository,
    InMemoryBusinessRepository,
    InMemoryCustomerRepository,
    InMemoryOwnerNotificationSender,
    InMemoryOwnerTelegramLinkRepository,
    InMemoryServiceRepository,
)
from frontdesk.infrastructure.system import SequentialIdGenerator

NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
BIZ = BusinessId("biz")


async def _world(
    *,
    locale: str = "en",
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    enabled: bool = True,
) -> tuple[OwnerNotifier, InMemoryOwnerNotificationSender]:
    links = InMemoryOwnerTelegramLinkRepository()
    await links.upsert(OwnerTelegramLink(BIZ, "owner-chat", "Owner", notifications_enabled=enabled))
    customers = InMemoryCustomerRepository(SequentialIdGenerator("cus"))
    customer = await customers.upsert(BIZ, Channel.TELEGRAM, "+1", "Fedor")
    appointments = InMemoryAppointmentRepository()
    appointments.appointments[AppointmentId("ap")] = Appointment(
        AppointmentId("ap"),
        BIZ,
        ServiceId("svc"),
        ResourceId("res"),
        customer.id,
        TimeSlot(NOW, NOW + timedelta(hours=1)),
        status,
    )
    sender = InMemoryOwnerNotificationSender()
    notifier = OwnerNotifier(
        links,
        appointments,
        InMemoryServiceRepository([Service(ServiceId("svc"), BIZ, "Haircut", 60)]),
        customers,
        InMemoryBusinessRepository([Business(BIZ, "Studio", "UTC", locale=locale)], {}),
        sender,
    )
    return notifier, sender


async def test_notifies_the_owner_on_a_booking() -> None:
    notifier, sender = await _world()

    await notifier.on_event(AppointmentBooked(BIZ, AppointmentId("ap")))

    assert len(sender.sent) == 1
    business_id, chat_id, message = sender.sent[0]
    assert (business_id, chat_id) == (BIZ, "owner-chat")
    assert "New booking" in message
    assert "Haircut" in message
    assert "Fedor" in message


async def test_marks_a_pending_booking_as_needing_confirmation() -> None:
    notifier, sender = await _world(status=AppointmentStatus.PENDING)

    await notifier.on_event(AppointmentBooked(BIZ, AppointmentId("ap")))

    assert "Needs your confirmation" in sender.sent[0][2]


async def test_uses_the_business_locale() -> None:
    notifier, sender = await _world(locale="ru")

    await notifier.on_event(AppointmentCancelled(BIZ, AppointmentId("ap")))

    assert "Отмена" in sender.sent[0][2]


async def test_skips_when_there_is_no_link() -> None:
    notifier, sender = await _world()
    notifier._links = InMemoryOwnerTelegramLinkRepository()  # no link stored

    await notifier.on_event(AppointmentBooked(BIZ, AppointmentId("ap")))

    assert sender.sent == []


async def test_skips_when_notifications_are_disabled() -> None:
    notifier, sender = await _world(enabled=False)

    await notifier.on_event(AppointmentRescheduled(BIZ, AppointmentId("ap")))

    assert sender.sent == []


async def test_ignores_an_owner_confirmation() -> None:
    notifier, sender = await _world()

    await notifier.on_event(AppointmentConfirmed(BIZ, AppointmentId("ap")))

    assert sender.sent == []  # the owner's own action — no self-notification
