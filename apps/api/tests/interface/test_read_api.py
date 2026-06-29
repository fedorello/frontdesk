"""The read API lists a business's appointments with service names, scoped."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.domain.enums import AppointmentStatus, Channel, MessageRole
from frontdesk.domain.ids import AppointmentId, BusinessId, CustomerId, ResourceId, ServiceId
from frontdesk.domain.models import (
    Appointment,
    Customer,
    IntakeAnswer,
    Message,
    Service,
    TimeSlot,
)
from frontdesk.infrastructure.memory import (
    InMemoryAppointmentRepository,
    InMemoryConversationRepository,
    InMemoryServiceRepository,
)
from frontdesk.interface.read_api import build_read_router


def _appt(
    identifier: str,
    service_id: str,
    hour: int,
    status: AppointmentStatus,
    intake: tuple[IntakeAnswer, ...] = (),
) -> Appointment:
    return Appointment(
        AppointmentId(identifier),
        BusinessId("biz"),
        ServiceId(service_id),
        ResourceId("r"),
        CustomerId("c"),
        TimeSlot(
            datetime(2026, 6, 26, hour, 0, tzinfo=UTC),
            datetime(2026, 6, 26, hour + 1, 0, tzinfo=UTC),
        ),
        status,
        intake,
    )


def _read_app(appointments: InMemoryAppointmentRepository) -> FastAPI:
    services = [
        Service(
            ServiceId("svc"), BusinessId("biz"), "Haircut", 60, resource_ids=(ResourceId("r"),)
        ),
        Service(
            ServiceId("svc2"), BusinessId("biz"), "Massage", 60, resource_ids=(ResourceId("r"),)
        ),
    ]
    app = FastAPI()
    app.include_router(
        build_read_router(appointments, InMemoryServiceRepository(services), _empty_conversations())
    )
    return app


async def test_lists_appointments_with_service_names() -> None:
    appointments = InMemoryAppointmentRepository()
    appointments.appointments[AppointmentId("a1")] = _appt(
        "a1", "svc", 9, AppointmentStatus.PENDING
    )

    transport = httpx.ASGITransport(app=_read_app(appointments))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        page = (await client.get("/api/businesses/biz/appointments")).json()
        assert page["total"] == 1
        assert page["items"][0]["service"] == "Haircut"  # resolved from the service id
        assert page["items"][0]["status"] == "pending"
        assert page["items"][0]["starts_at"].startswith("2026-06-26T09:00")

        other = (await client.get("/api/businesses/other/appointments")).json()
        assert other == {"items": [], "total": 0}  # another business sees nothing


async def test_appointments_are_paginated_filtered_and_searchable() -> None:
    appointments = InMemoryAppointmentRepository()
    for appointment in [
        _appt("a1", "svc", 9, AppointmentStatus.CONFIRMED),
        _appt("a2", "svc", 10, AppointmentStatus.CONFIRMED),
        _appt("a3", "svc2", 11, AppointmentStatus.CONFIRMED, (IntakeAnswer("Note", "vip"),)),
        _appt("a4", "svc", 12, AppointmentStatus.CANCELLED),
    ]:
        appointments.appointments[appointment.id] = appointment

    transport = httpx.ASGITransport(app=_read_app(appointments))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def page(query: str) -> httpx.Response:
            return await client.get(f"/api/businesses/biz/appointments?{query}")

        first = (await page("limit=2&offset=0")).json()
        assert first["total"] == 3  # active count, cancelled excluded by default
        assert [item["id"] for item in first["items"]] == ["a1", "a2"]  # ordered by start

        second = (await page("limit=2&offset=2")).json()
        assert [item["id"] for item in second["items"]] == ["a3"]  # the last active one

        assert (await page("include_cancelled=true&limit=10")).json()["total"] == 4  # +cancelled
        assert [i["id"] for i in (await page("q=massage")).json()["items"]] == [
            "a3"
        ]  # service name
        assert [i["id"] for i in (await page("q=a1")).json()["items"]] == ["a1"]  # appointment id
        assert [i["id"] for i in (await page("q=vip")).json()["items"]] == ["a3"]  # intake answer
        assert (await page("limit=999")).json()["total"] == 3  # an oversized limit is capped


def _empty_conversations() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


async def test_lists_recent_conversations() -> None:
    conversations = InMemoryConversationRepository()
    customer = Customer(CustomerId("c"), BusinessId("biz"), Channel.TELEGRAM, "55501")
    await conversations.append(customer, Message(MessageRole.CUSTOMER, "Can I book?", _NOW))
    await conversations.append(customer, Message(MessageRole.ASSISTANT, "Sure!", _NOW))

    app = FastAPI()
    app.include_router(
        build_read_router(
            InMemoryAppointmentRepository(), InMemoryServiceRepository([]), conversations
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        feed = (await client.get("/api/businesses/biz/conversations")).json()
        assert [m["text"] for m in feed] == ["Sure!", "Can I book?"]  # most recent first
        assert feed[0]["customer"] == "55501"
        assert (await client.get("/api/businesses/other/conversations")).json() == []


_NOW = datetime(2026, 6, 26, 9, 0, tzinfo=UTC)
