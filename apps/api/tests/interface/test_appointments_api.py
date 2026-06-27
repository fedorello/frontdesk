"""The confirm endpoint: 200 on success, 404 for unknown/foreign, 409 for a bad transition."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.appointments import ConfirmAppointment
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import AppointmentId, ResourceId
from frontdesk.domain.models import TimeSlot
from frontdesk.interface.appointments_api import build_appointments_router
from tests.application.world import World, build_world

_SLOT = TimeSlot(datetime(2026, 6, 26, 15, tzinfo=UTC), datetime(2026, 6, 26, 16, tzinfo=UTC))


def _client(world: World) -> httpx.AsyncClient:
    confirm = ConfirmAppointment(world.appointments, world.calendar, world.events)
    app = FastAPI()
    app.include_router(build_appointments_router(confirm))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _pending_booking(world: World) -> str:
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    appointment = await world.book(world.service, ResourceId("res"), customer, _SLOT)
    return str(appointment.id)


async def test_confirm_endpoint_confirms_a_pending_booking() -> None:
    world = build_world([], requires_confirmation=True)
    appointment_id = await _pending_booking(world)
    async with _client(world) as client:
        response = await client.post(f"/api/businesses/biz/appointments/{appointment_id}/confirm")
    assert response.status_code == 200
    assert response.json() == {"id": appointment_id, "status": "confirmed"}


async def test_confirm_endpoint_404_for_unknown_appointment() -> None:
    world = build_world([])
    async with _client(world) as client:
        response = await client.post("/api/businesses/biz/appointments/ghost/confirm")
    assert response.status_code == 404


async def test_confirm_endpoint_404_for_another_business() -> None:
    world = build_world([], requires_confirmation=True)
    appointment_id = await _pending_booking(world)
    async with _client(world) as client:
        response = await client.post(
            f"/api/businesses/someone-else/appointments/{appointment_id}/confirm"
        )
    assert response.status_code == 404  # never leak that it exists


async def test_confirm_endpoint_409_for_a_cancelled_appointment() -> None:
    world = build_world([], requires_confirmation=True)
    appointment_id = await _pending_booking(world)
    await world.cancel(AppointmentId(appointment_id))
    async with _client(world) as client:
        response = await client.post(f"/api/businesses/biz/appointments/{appointment_id}/confirm")
    assert response.status_code == 409
