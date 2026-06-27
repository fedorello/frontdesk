"""Owner-facing appointment actions for the dashboard (M5): confirm, cancel, reschedule."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from frontdesk.application.appointments import ConfirmAppointment
from frontdesk.application.owner_actions import (
    OwnerCancelAppointment,
    OwnerRescheduleAppointment,
)
from frontdesk.domain.errors import (
    AppointmentNotFound,
    DomainError,
    InvalidTransition,
    TenantMismatch,
)
from frontdesk.domain.ids import AppointmentId, BusinessId
from frontdesk.domain.models import Appointment

Guard = Callable[..., Awaitable[None]] | None

_CONFLICT = 409
_NOT_FOUND = 404
_UNPROCESSABLE = 422
_MAX_REASON = 1000


class ConfirmationResult(BaseModel):
    id: str
    status: str


class CancelInput(BaseModel):
    reason: str = Field(default="", max_length=_MAX_REASON)


class RescheduleInput(BaseModel):
    start: str  # ISO 8601


class AppointmentResult(BaseModel):
    id: str
    status: str
    starts_at: str
    ends_at: str


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def build_appointments_router(
    confirm: ConfirmAppointment,
    cancel: OwnerCancelAppointment,
    reschedule: OwnerRescheduleAppointment,
    guard: Guard = None,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])
    base = "/api/businesses/{business_id}/appointments/{appointment_id}"

    @router.post(f"{base}/confirm")
    async def confirm_appointment(business_id: str, appointment_id: str) -> ConfirmationResult:
        try:
            appointment = await confirm(BusinessId(business_id), AppointmentId(appointment_id))
        except (AppointmentNotFound, TenantMismatch) as error:
            raise HTTPException(_NOT_FOUND, "appointment not found") from error
        except InvalidTransition as error:
            raise HTTPException(_CONFLICT, str(error)) from error
        return ConfirmationResult(id=str(appointment.id), status=appointment.status.value)

    @router.post(f"{base}/cancel")
    async def cancel_appointment(
        business_id: str, appointment_id: str, body: CancelInput
    ) -> AppointmentResult:
        try:
            appointment = await cancel(
                BusinessId(business_id), AppointmentId(appointment_id), body.reason
            )
        except (AppointmentNotFound, TenantMismatch) as error:
            raise HTTPException(_NOT_FOUND, "appointment not found") from error
        return _result(appointment)

    @router.post(f"{base}/reschedule")
    async def reschedule_appointment(
        business_id: str, appointment_id: str, body: RescheduleInput
    ) -> AppointmentResult:
        start = _parse_iso(body.start)
        if start is None:
            raise HTTPException(_UNPROCESSABLE, "invalid start time")
        try:
            appointment = await reschedule(
                BusinessId(business_id), AppointmentId(appointment_id), start
            )
        except (AppointmentNotFound, TenantMismatch) as error:
            raise HTTPException(_NOT_FOUND, "appointment not found") from error
        except DomainError as error:  # slot taken / outside hours / past
            raise HTTPException(_CONFLICT, str(error)) from error
        return _result(appointment)

    return router


def _result(appointment: Appointment) -> AppointmentResult:
    return AppointmentResult(
        id=str(appointment.id),
        status=appointment.status.value,
        starts_at=appointment.slot.starts_at.isoformat(),
        ends_at=appointment.slot.ends_at.isoformat(),
    )
