"""The owner appointment endpoints: confirm, cancel (with reason → customer), reschedule."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.appointments import ConfirmAppointment
from frontdesk.application.owner_actions import (
    OwnerCancelAppointment,
    OwnerRescheduleAppointment,
)
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import ResourceId
from frontdesk.domain.models import Business, Customer, TimeSlot
from frontdesk.interface.appointments_api import build_appointments_router
from tests.application.world import World, build_world

_SLOT = TimeSlot(datetime(2026, 6, 26, 15, tzinfo=UTC), datetime(2026, 6, 26, 16, tzinfo=UTC))


class FakeNotifier:
    """Records the messages the owner actions would send to the customer."""

    def __init__(self) -> None:
        self.sent: list[tuple[Customer, str]] = []

    async def notify(self, business: Business, customer: Customer, text: str) -> None:
        self.sent.append((customer, text))


def _client(world: World, notifier: FakeNotifier) -> httpx.AsyncClient:
    deps = world.deps
    router = build_appointments_router(
        ConfirmAppointment(world.appointments, world.calendar, world.events),
        OwnerCancelAppointment(
            deps.appointments,
            deps.services,
            deps.businesses,
            deps.customers,
            world.cancel,
            notifier,
        ),
        OwnerRescheduleAppointment(
            deps.appointments,
            deps.services,
            deps.businesses,
            deps.customers,
            world.reschedule,
            notifier,
        ),
    )
    app = FastAPI()
    app.include_router(router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _booking(world: World) -> str:
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    appointment = await world.book(world.service, ResourceId("res"), customer, _SLOT)
    return str(appointment.id)


async def test_confirm_endpoint_confirms_a_pending_booking() -> None:
    world = build_world([], requires_confirmation=True)
    notifier = FakeNotifier()
    appointment_id = await _booking(world)
    async with _client(world, notifier) as client:
        response = await client.post(f"/api/businesses/biz/appointments/{appointment_id}/confirm")
    assert response.status_code == 200
    assert response.json() == {"id": appointment_id, "status": "confirmed"}


async def test_confirm_endpoint_404_for_unknown_appointment() -> None:
    world = build_world([])
    async with _client(world, FakeNotifier()) as client:
        response = await client.post("/api/businesses/biz/appointments/ghost/confirm")
    assert response.status_code == 404


async def test_cancel_endpoint_cancels_and_messages_the_customer_with_the_reason() -> None:
    world = build_world([])
    notifier = FakeNotifier()
    appointment_id = await _booking(world)
    async with _client(world, notifier) as client:
        response = await client.post(
            f"/api/businesses/biz/appointments/{appointment_id}/cancel",
            json={"reason": "The astrologer is unwell"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert any("The astrologer is unwell" in text for _, text in notifier.sent)


async def test_cancel_endpoint_404_for_another_business() -> None:
    world = build_world([])
    appointment_id = await _booking(world)
    async with _client(world, FakeNotifier()) as client:
        response = await client.post(
            f"/api/businesses/someone-else/appointments/{appointment_id}/cancel", json={}
        )
    assert response.status_code == 404


async def test_reschedule_endpoint_moves_and_notifies() -> None:
    world = build_world([])
    notifier = FakeNotifier()
    appointment_id = await _booking(world)
    async with _client(world, notifier) as client:
        response = await client.post(
            f"/api/businesses/biz/appointments/{appointment_id}/reschedule",
            json={"start": "2026-06-26T16:00:00+00:00"},
        )
    assert response.status_code == 200
    assert response.json()["starts_at"] == "2026-06-26T16:00:00+00:00"
    assert len(notifier.sent) == 1  # the customer was told the new time


async def test_reschedule_endpoint_422_for_a_bad_time() -> None:
    world = build_world([])
    appointment_id = await _booking(world)
    async with _client(world, FakeNotifier()) as client:
        response = await client.post(
            f"/api/businesses/biz/appointments/{appointment_id}/reschedule",
            json={"start": "not-a-date"},
        )
    assert response.status_code == 422


async def test_reschedule_endpoint_404_for_unknown_appointment() -> None:
    world = build_world([])
    async with _client(world, FakeNotifier()) as client:
        response = await client.post(
            "/api/businesses/biz/appointments/ghost/reschedule",
            json={"start": "2026-06-26T16:00:00+00:00"},
        )
    assert response.status_code == 404
