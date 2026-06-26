"""Read endpoints for the dashboard (M5): live, business-scoped data."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from frontdesk.application.ports import (
    AppointmentRepository,
    ConversationRepository,
    ServiceRepository,
)
from frontdesk.domain.ids import BusinessId

Guard = Callable[..., Awaitable[None]] | None


class AppointmentView(BaseModel):
    service: str
    starts_at: str
    ends_at: str
    status: str


class MessageView(BaseModel):
    customer: str
    role: str
    text: str
    at: str


def build_read_router(
    appointments: AppointmentRepository,
    services: ServiceRepository,
    conversations: ConversationRepository,
    guard: Guard = None,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/conversations")
    async def list_conversations(business_id: str) -> list[MessageView]:
        return [
            MessageView(
                customer=message.customer,
                role=message.role,
                text=message.text,
                at=message.at.isoformat(),
            )
            for message in await conversations.recent_for_business(BusinessId(business_id))
        ]

    @router.get("/api/businesses/{business_id}/appointments")
    async def list_appointments(business_id: str) -> list[AppointmentView]:
        bid = BusinessId(business_id)
        names = {s.id: s.name for s in await services.for_business(bid)}
        return [
            AppointmentView(
                service=names.get(appointment.service_id, str(appointment.service_id)),
                starts_at=appointment.slot.starts_at.isoformat(),
                ends_at=appointment.slot.ends_at.isoformat(),
                status=appointment.status.value,
            )
            for appointment in await appointments.for_business(bid)
        ]

    return router
