"""Owner-driven appointment actions that also notify the customer over the bot.

The owner cancels (with a reason) or reschedules from the dashboard; the customer gets a
plain, localized message on the business's own Telegram bot. Tenant-scoped throughout.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from frontdesk.application.appointments import CancelAppointment, RescheduleAppointment
from frontdesk.application.ports import (
    AppointmentRepository,
    BusinessRepository,
    CustomerNotifier,
    CustomerRepository,
    ServiceRepository,
)
from frontdesk.domain.errors import TenantMismatch
from frontdesk.domain.ids import AppointmentId, BusinessId
from frontdesk.domain.models import Appointment, Business, Service, TimeSlot

_WHEN_FORMAT = "%a %d %b %H:%M"  # rendered in the business's local time zone

# (header, reason line) per locale; the reason line is dropped when no reason is given.
_CANCEL_NOTICE = {
    "en": ("❌ Your booking for {service} on {when} has been cancelled.", "Reason: {reason}"),
    "es": ("❌ Tu reserva de {service} el {when} ha sido cancelada.", "Motivo: {reason}"),
    "ru": ("❌ Ваша запись на {service} ({when}) отменена.", "Причина: {reason}"),
    "zh": ("❌ 您预约的 {service}（{when}）已取消。", "原因：{reason}"),
}

_RESCHEDULE_NOTICE = {
    "en": "🔄 Your booking for {service} has been moved to {when}.",
    "es": "🔄 Tu reserva de {service} se ha cambiado a {when}.",
    "ru": "🔄 Ваша запись на {service} перенесена на {when}.",
    "zh": "🔄 您预约的 {service} 已改到 {when}。",
}


def _when(slot: TimeSlot, business: Business) -> str:
    return slot.starts_at.astimezone(ZoneInfo(business.timezone)).strftime(_WHEN_FORMAT)


def cancel_notice(business: Business, service: Service, slot: TimeSlot, reason: str) -> str:
    header, reason_line = _CANCEL_NOTICE.get(business.locale, _CANCEL_NOTICE["en"])
    text = header.format(service=service.name, when=_when(slot, business))
    if reason.strip():
        text += "\n" + reason_line.format(reason=reason.strip())
    return text


def reschedule_notice(business: Business, service: Service, slot: TimeSlot) -> str:
    template = _RESCHEDULE_NOTICE.get(business.locale, _RESCHEDULE_NOTICE["en"])
    return template.format(service=service.name, when=_when(slot, business))


class OwnerCancelAppointment:
    """Cancel a booking on the owner's behalf and tell the customer why."""

    def __init__(
        self,
        appointments: AppointmentRepository,
        services: ServiceRepository,
        businesses: BusinessRepository,
        customers: CustomerRepository,
        cancel: CancelAppointment,
        notifier: CustomerNotifier,
    ) -> None:
        self._appointments = appointments
        self._services = services
        self._businesses = businesses
        self._customers = customers
        self._cancel = cancel
        self._notifier = notifier

    async def __call__(
        self, business_id: BusinessId, appointment_id: AppointmentId, reason: str
    ) -> Appointment:
        appointment = await self._appointments.get(appointment_id)
        if appointment.business_id != business_id:
            raise TenantMismatch("appointment belongs to another business")
        business = await self._businesses.get(business_id)
        service = await self._services.get(appointment.service_id)
        customer = await self._customers.get(appointment.customer_id)
        cancelled = await self._cancel(appointment_id)
        await self._notifier.notify(
            business, customer, cancel_notice(business, service, appointment.slot, reason)
        )
        return cancelled


class OwnerRescheduleAppointment:
    """Move a booking on the owner's behalf and tell the customer the new time."""

    def __init__(
        self,
        appointments: AppointmentRepository,
        services: ServiceRepository,
        businesses: BusinessRepository,
        customers: CustomerRepository,
        reschedule: RescheduleAppointment,
        notifier: CustomerNotifier,
    ) -> None:
        self._appointments = appointments
        self._services = services
        self._businesses = businesses
        self._customers = customers
        self._reschedule = reschedule
        self._notifier = notifier

    async def __call__(
        self, business_id: BusinessId, appointment_id: AppointmentId, start: datetime
    ) -> Appointment:
        appointment = await self._appointments.get(appointment_id)
        if appointment.business_id != business_id:
            raise TenantMismatch("appointment belongs to another business")
        business = await self._businesses.get(business_id)
        service = await self._services.get(appointment.service_id)
        customer = await self._customers.get(appointment.customer_id)
        slot = TimeSlot(start, start + timedelta(minutes=service.duration_minutes))
        moved = await self._reschedule(appointment_id, slot)
        await self._notifier.notify(
            business, customer, reschedule_notice(business, service, moved.slot)
        )
        return moved
