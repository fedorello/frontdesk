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


class IntakeAnswerView(BaseModel):
    name: str
    value: str


class AppointmentView(BaseModel):
    id: str
    service: str
    starts_at: str
    ends_at: str
    status: str
    intake: list[IntakeAnswerView] = []


class MessageView(BaseModel):
    customer: str
    customer_id: str
    customer_name: str | None = None
    role: str
    text: str
    at: str
    handled: bool


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
                customer_id=message.customer_id,
                customer_name=message.customer_name,
                role=message.role,
                text=message.text,
                at=message.at.isoformat(),
                handled=message.handled,
            )
            for message in await conversations.recent_for_business(BusinessId(business_id))
        ]

    @router.get("/api/businesses/{business_id}/appointments")
    async def list_appointments(business_id: str) -> list[AppointmentView]:
        bid = BusinessId(business_id)
        names = {s.id: s.name for s in await services.for_business(bid)}
        return [
            AppointmentView(
                id=str(appointment.id),
                service=names.get(appointment.service_id, str(appointment.service_id)),
                starts_at=appointment.slot.starts_at.isoformat(),
                ends_at=appointment.slot.ends_at.isoformat(),
                status=appointment.status.value,
                intake=[IntakeAnswerView(name=a.name, value=a.value) for a in appointment.intake],
            )
            for appointment in await appointments.for_business(bid)
        ]

    return router
