"""Read endpoints for the dashboard (M5): live, business-scoped data."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from frontdesk.application.ports import (
    AppointmentQuery,
    AppointmentRepository,
    ConversationRepository,
    ServiceRepository,
)
from frontdesk.domain.ids import BusinessId, ServiceId
from frontdesk.domain.models import Appointment

Guard = Callable[..., Awaitable[None]] | None

# Server-side pagination of the appointments list. The client asks for a page size; the server
# caps it so a single request can never pull an unbounded number of rows.
_DEFAULT_PAGE_SIZE = 8
_MAX_PAGE_SIZE = 50


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


class AppointmentPageView(BaseModel):
    items: list[AppointmentView]
    total: int  # matching appointments across all pages, for the page count


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
    async def list_appointments(
        business_id: str,
        limit: int = _DEFAULT_PAGE_SIZE,
        offset: int = 0,
        include_cancelled: bool = False,
        q: str = "",
    ) -> AppointmentPageView:
        bid = BusinessId(business_id)
        names = {s.id: s.name for s in await services.for_business(bid)}
        # Resolve service-NAME matches to ids here, so the repository never needs the catalogue.
        search = q.strip().lower()
        service_ids = tuple(sid for sid, name in names.items() if search and search in name.lower())
        query = AppointmentQuery(
            include_cancelled=include_cancelled,
            search=search,
            service_ids=service_ids,
            limit=min(max(limit, 1), _MAX_PAGE_SIZE),
            offset=max(offset, 0),
        )
        items, total = await appointments.page_for_business(bid, query)
        return AppointmentPageView(
            items=[_appointment_view(appointment, names) for appointment in items],
            total=total,
        )

    return router


def _appointment_view(appointment: Appointment, names: dict[ServiceId, str]) -> AppointmentView:
    return AppointmentView(
        id=str(appointment.id),
        service=names.get(appointment.service_id, str(appointment.service_id)),
        starts_at=appointment.slot.starts_at.isoformat(),
        ends_at=appointment.slot.ends_at.isoformat(),
        status=appointment.status.value,
        intake=[IntakeAnswerView(name=a.name, value=a.value) for a in appointment.intake],
    )
