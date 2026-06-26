"""Reusable port-contract checks.

Any adapter — the in-memory fakes now, the real Postgres/Redis adapters later —
must pass these. Not collected by pytest itself (no ``test_`` prefix); imported
and run by the adapter test modules.
"""

from datetime import UTC, datetime, time, timedelta

import pytest

from frontdesk.application.ports import (
    AppointmentRepository,
    BusinessRepository,
    Calendar,
    ConversationRepository,
    CustomerRepository,
    LlmConfig,
    LlmConfigRepository,
    ReminderStore,
    TelegramBotConfig,
    TelegramBotRepository,
)
from frontdesk.domain.enums import AppointmentStatus, Channel, MessageRole
from frontdesk.domain.errors import AppointmentNotFound, DomainError
from frontdesk.domain.ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import (
    Business,
    Customer,
    Message,
    Reminder,
    Resource,
    Service,
    WorkingHours,
)

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)  # a Friday, 09:00 Montevideo


def make_business() -> Business:
    return Business(BusinessId("biz"), "Studio", "UTC", lead_time_minutes=0, buffer_minutes=0)


def make_resource() -> Resource:
    hours = tuple(WorkingHours(day, time(9), time(17)) for day in range(7))
    return Resource(ResourceId("res"), BusinessId("biz"), "Ana", hours)


def make_service() -> Service:
    return Service(
        ServiceId("svc"), BusinessId("biz"), "Haircut", 60, resource_ids=(ResourceId("res"),)
    )


def make_customer() -> Customer:
    return Customer(CustomerId("cus"), BusinessId("biz"), Channel.WHATSAPP, "+100")


async def check_reminder_store(store: ReminderStore) -> None:
    business_id, appt_id = BusinessId("biz"), AppointmentId("appt")
    due = Reminder(ReminderId("r-due"), business_id, appt_id, NOW - timedelta(minutes=1), "24h")
    later = Reminder(ReminderId("r-later"), business_id, appt_id, NOW + timedelta(hours=1), "2h")
    await store.schedule([due, later])

    claimed = await store.claim_due(NOW)
    assert [r.id for r in claimed] == [due.id]  # only the due one

    await store.mark_sent(due.id)
    assert await store.claim_due(NOW) == []  # sent → no longer due

    await store.cancel_for(appt_id)  # cancels the remaining pending one
    assert await store.claim_due(NOW + timedelta(hours=2)) == []


async def check_calendar(calendar: Calendar) -> None:
    service, customer = make_service(), make_customer()
    resource_id = ResourceId("res")

    slots = await calendar.find_availability(service, NOW)
    assert slots, "expected free slots"
    first = slots[0]

    appointment = await calendar.book(service, resource_id, customer, first)
    assert appointment.status == AppointmentStatus.PENDING

    with pytest.raises(DomainError):
        await calendar.book(service, resource_id, customer, first)  # double-book rejected

    later = (await calendar.find_availability(service, NOW))[0]
    assert later != first  # the booked slot is no longer offered
    moved = await calendar.move(appointment.id, later)
    assert moved.slot == later

    cancelled = await calendar.cancel(appointment.id)
    assert cancelled.status == AppointmentStatus.CANCELLED


async def check_business_repository(repo: BusinessRepository) -> None:
    found = await repo.for_channel(Channel.WHATSAPP, "+100")
    assert found is not None
    assert found.id == BusinessId("biz")
    assert await repo.for_channel(Channel.WHATSAPP, "+999") is None
    assert (await repo.get(BusinessId("biz"))).id == BusinessId("biz")


async def check_customer_repository(repo: CustomerRepository) -> None:
    first = await repo.upsert(BusinessId("biz"), Channel.WHATSAPP, "+100")
    again = await repo.upsert(BusinessId("biz"), Channel.WHATSAPP, "+100")
    other = await repo.upsert(BusinessId("biz"), Channel.WHATSAPP, "+200")

    assert first.id == again.id  # idempotent
    assert other.id != first.id


async def check_conversation_repository(repo: ConversationRepository) -> None:
    customer = make_customer()
    for index in range(3):
        await repo.append(customer, Message(MessageRole.CUSTOMER, f"msg-{index}", NOW))

    history = await repo.history(customer, limit=2)
    assert [m.text for m in history] == ["msg-1", "msg-2"]  # last 2, in order


async def check_appointment_repository(repo: AppointmentRepository) -> None:
    with pytest.raises(AppointmentNotFound):
        await repo.get(AppointmentId("missing"))


async def check_telegram_bot_repository(repo: TelegramBotRepository) -> None:
    biz = BusinessId("biz")
    assert await repo.get(biz) is None

    await repo.upsert(
        TelegramBotConfig(biz, "123:ABCDEF", "wh-secret", "ana_bot", webhook_set=False)
    )
    stored = await repo.get(biz)
    assert stored is not None
    assert stored.bot_token == "123:ABCDEF"  # decrypted back from storage
    assert stored.username == "ana_bot"
    assert stored.webhook_set is False

    await repo.upsert(
        TelegramBotConfig(biz, "123:ABCDEF", "wh-secret", "ana_bot", webhook_set=True)
    )
    updated = await repo.get(biz)
    assert updated is not None
    assert updated.webhook_set is True  # upsert updates in place


async def check_llm_config_repository(repo: LlmConfigRepository) -> None:
    biz = BusinessId("biz")
    assert await repo.get(biz) is None

    await repo.upsert(
        LlmConfig(biz, "own", "openai", "gpt-x", None, api_key="sk-secret-xyz", api_key_hint="xyz")
    )
    stored = await repo.get(biz)
    assert stored is not None
    assert stored.mode == "own"
    assert stored.provider == "openai"
    assert stored.api_key == "sk-secret-xyz"  # decrypted back
    assert stored.api_key_hint == "xyz"

    await repo.upsert(LlmConfig(biz, "default"))
    reverted = await repo.get(biz)
    assert reverted is not None
    assert reverted.mode == "default"
    assert reverted.api_key is None
