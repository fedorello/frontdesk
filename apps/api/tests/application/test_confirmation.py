"""Owner-driven confirmation: the domain transition, the initial-status rule, the use case."""

from datetime import UTC, datetime

import pytest

from frontdesk.application.appointments import ConfirmAppointment
from frontdesk.application.ports import AppointmentConfirmed
from frontdesk.domain.enums import AppointmentStatus, Channel
from frontdesk.domain.errors import AppointmentNotFound, InvalidTransition, TenantMismatch
from frontdesk.domain.ids import (
    AppointmentId,
    BusinessId,
    CustomerId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import (
    Appointment,
    Service,
    TimeSlot,
    initial_appointment_status,
)
from tests.application.world import build_world

_SLOT = TimeSlot(datetime(2026, 6, 26, 15, tzinfo=UTC), datetime(2026, 6, 26, 16, tzinfo=UTC))


def _appointment(status: AppointmentStatus) -> Appointment:
    return Appointment(
        AppointmentId("a"),
        BusinessId("biz"),
        ServiceId("svc"),
        ResourceId("res"),
        CustomerId("c"),
        _SLOT,
        status=status,
    )


def _service(*, requires_confirmation: bool) -> Service:
    return Service(
        ServiceId("svc"),
        BusinessId("biz"),
        "Reading",
        60,
        requires_confirmation=requires_confirmation,
    )


def test_confirmed_transitions_pending_to_confirmed() -> None:
    assert _appointment(AppointmentStatus.PENDING).confirmed().status == AppointmentStatus.CONFIRMED


def test_confirmed_is_idempotent() -> None:
    already = _appointment(AppointmentStatus.CONFIRMED)
    assert already.confirmed().status == AppointmentStatus.CONFIRMED


def test_confirmed_rejects_a_cancelled_appointment() -> None:
    with pytest.raises(InvalidTransition):
        _appointment(AppointmentStatus.CANCELLED).confirmed()


def test_initial_status_follows_the_service_flag() -> None:
    assert initial_appointment_status(_service(requires_confirmation=True)) == (
        AppointmentStatus.PENDING
    )
    assert initial_appointment_status(_service(requires_confirmation=False)) == (
        AppointmentStatus.CONFIRMED
    )


async def test_confirm_use_case_confirms_a_pending_booking_and_publishes() -> None:
    world = build_world([], requires_confirmation=True)
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    appointment = await world.book(world.service, ResourceId("res"), customer, _SLOT)
    assert appointment.status == AppointmentStatus.PENDING  # owner must confirm

    confirm = ConfirmAppointment(world.appointments, world.calendar, world.events)
    confirmed = await confirm(world.business.id, appointment.id)

    assert confirmed.status == AppointmentStatus.CONFIRMED
    assert any(isinstance(event, AppointmentConfirmed) for event in world.events.events)


async def test_confirm_use_case_refuses_another_business() -> None:
    world = build_world([], requires_confirmation=True)
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    appointment = await world.book(world.service, ResourceId("res"), customer, _SLOT)
    confirm = ConfirmAppointment(world.appointments, world.calendar, world.events)

    with pytest.raises(TenantMismatch):
        await confirm(BusinessId("someone-else"), appointment.id)


async def test_confirm_use_case_raises_for_unknown_appointment() -> None:
    world = build_world([])
    confirm = ConfirmAppointment(world.appointments, world.calendar, world.events)

    with pytest.raises(AppointmentNotFound):
        await confirm(world.business.id, AppointmentId("nope"))
