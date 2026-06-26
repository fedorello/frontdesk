"""The read API lists a business's appointments with service names, scoped."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.domain.enums import AppointmentStatus
from frontdesk.domain.ids import AppointmentId, BusinessId, CustomerId, ResourceId, ServiceId
from frontdesk.domain.models import Appointment, Service, TimeSlot
from frontdesk.infrastructure.memory import (
    InMemoryAppointmentRepository,
    InMemoryServiceRepository,
)
from frontdesk.interface.read_api import build_read_router


async def test_lists_appointments_with_service_names() -> None:
    appointments = InMemoryAppointmentRepository()
    appointments.appointments[AppointmentId("a1")] = Appointment(
        AppointmentId("a1"),
        BusinessId("biz"),
        ServiceId("svc"),
        ResourceId("r"),
        CustomerId("c"),
        TimeSlot(datetime(2026, 6, 26, 9, 0, tzinfo=UTC), datetime(2026, 6, 26, 10, 0, tzinfo=UTC)),
        AppointmentStatus.PENDING,
    )
    service = Service(
        ServiceId("svc"), BusinessId("biz"), "Haircut", 60, resource_ids=(ResourceId("r"),)
    )

    app = FastAPI()
    app.include_router(build_read_router(appointments, InMemoryServiceRepository([service])))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listed = (await client.get("/api/businesses/biz/appointments")).json()
        assert len(listed) == 1
        assert listed[0]["service"] == "Haircut"  # resolved from the service id
        assert listed[0]["status"] == "pending"
        assert listed[0]["starts_at"].startswith("2026-06-26T09:00")

        # another business sees nothing
        assert (await client.get("/api/businesses/other/appointments")).json() == []
