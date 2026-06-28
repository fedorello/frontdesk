"""The worker use case: send the reminders that are due."""

from datetime import datetime

from frontdesk.application.datetime_format import format_when
from frontdesk.application.ports import (
    AppointmentRepository,
    BusinessRepository,
    CustomerRepository,
    MessagingPort,
    OutboundMessage,
    ReminderStore,
    ServiceRepository,
)

# Localized by the studio's chosen language (business.locale), like the booking receipt.
_REMINDER = {
    "en": "Reminder: your {service} is {when}. See you then!",
    "es": "Recordatorio: tu {service} es {when}. ¡Te esperamos!",
    "ru": "Напоминание: ваша запись «{service}» — {when}. Ждём вас!",
    "zh": "提醒：您预约的{service}在 {when}。到时见！",
}
_BUTTONS = {
    "en": ("Confirm", "Reschedule"),
    "es": ("Confirmar", "Reprogramar"),
    "ru": ("Подтвердить", "Перенести"),
    "zh": ("确认", "改期"),
}


class SendDueReminders:
    """Claim due reminders, send them with one-tap buttons, mark them sent."""

    def __init__(
        self,
        reminders: ReminderStore,
        appointments: AppointmentRepository,
        customers: CustomerRepository,
        services: ServiceRepository,
        businesses: BusinessRepository,
        messaging: MessagingPort,
    ) -> None:
        self._reminders = reminders
        self._appointments = appointments
        self._customers = customers
        self._services = services
        self._businesses = businesses
        self._messaging = messaging

    async def __call__(self, now: datetime) -> int:
        due = await self._reminders.claim_due(now)
        for reminder in due:
            appointment = await self._appointments.get(reminder.appointment_id)
            customer = await self._customers.get(appointment.customer_id)
            service = await self._services.get(appointment.service_id)
            business = await self._businesses.get(appointment.business_id)
            locale = business.locale if business.locale in _REMINDER else "en"
            # Studio's language + time zone (format_when localizes and adds the UTC offset).
            text = _REMINDER[locale].format(
                service=service.name, when=format_when(appointment.slot.starts_at, business)
            )
            await self._messaging.send(customer, OutboundMessage(text, buttons=_BUTTONS[locale]))
            await self._reminders.mark_sent(reminder.id)
        return len(due)
