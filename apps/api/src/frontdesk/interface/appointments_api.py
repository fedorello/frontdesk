"""Owner-facing appointment actions for the dashboard (M5): confirm a booking."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.appointments import ConfirmAppointment
from frontdesk.domain.errors import AppointmentNotFound, InvalidTransition, TenantMismatch
from frontdesk.domain.ids import AppointmentId, BusinessId

Guard = Callable[..., Awaitable[None]] | None

_CONFLICT = 409
_NOT_FOUND = 404


class ConfirmationResult(BaseModel):
    id: str
    status: str


def build_appointments_router(confirm: ConfirmAppointment, guard: Guard = None) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.post("/api/businesses/{business_id}/appointments/{appointment_id}/confirm")
    async def confirm_appointment(business_id: str, appointment_id: str) -> ConfirmationResult:
        try:
            appointment = await confirm(BusinessId(business_id), AppointmentId(appointment_id))
        except (AppointmentNotFound, TenantMismatch) as error:
            # Same response for "missing" and "another tenant's" — never leak existence.
            raise HTTPException(_NOT_FOUND, "appointment not found") from error
        except InvalidTransition as error:
            raise HTTPException(_CONFLICT, str(error)) from error
        return ConfirmationResult(id=str(appointment.id), status=appointment.status.value)

    return router
