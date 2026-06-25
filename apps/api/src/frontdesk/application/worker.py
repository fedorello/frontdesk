"""The worker use case: send the reminders that are due."""

from datetime import datetime

from frontdesk.application.ports import (
    AppointmentRepository,
    CustomerRepository,
    MessagingPort,
    OutboundMessage,
    ReminderStore,
    ServiceRepository,
)

CONFIRM = "Confirm"
RESCHEDULE = "Reschedule"


class SendDueReminders:
    """Claim due reminders, send them with one-tap buttons, mark them sent."""

    def __init__(
        self,
        reminders: ReminderStore,
        appointments: AppointmentRepository,
        customers: CustomerRepository,
        services: ServiceRepository,
        messaging: MessagingPort,
    ) -> None:
        self._reminders = reminders
        self._appointments = appointments
        self._customers = customers
        self._services = services
        self._messaging = messaging

    async def __call__(self, now: datetime) -> int:
        due = await self._reminders.claim_due(now)
        for reminder in due:
            appointment = await self._appointments.get(reminder.appointment_id)
            customer = await self._customers.get(appointment.customer_id)
            service = await self._services.get(appointment.service_id)
            when = appointment.slot.starts_at.strftime("%a %d %b at %H:%M UTC")
            text = f"Reminder: your {service.name} is {when}. See you then!"
            await self._messaging.send(
                customer, OutboundMessage(text, buttons=(CONFIRM, RESCHEDULE))
            )
            await self._reminders.mark_sent(reminder.id)
        return len(due)
