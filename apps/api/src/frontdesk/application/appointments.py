"""Booking use cases: book, reschedule, cancel — with reminder scheduling."""

from datetime import timedelta

from frontdesk.application.ports import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentConfirmed,
    AppointmentRepository,
    Calendar,
    Clock,
    EventPublisher,
    IdGenerator,
    ReminderStore,
)
from frontdesk.domain.errors import TenantMismatch
from frontdesk.domain.ids import AppointmentId, BusinessId, ReminderId, ResourceId
from frontdesk.domain.models import (
    Appointment,
    Customer,
    IntakeAnswer,
    Reminder,
    Service,
    TimeSlot,
)

# When to remind, before the appointment.
REMINDER_OFFSETS: tuple[tuple[str, int], ...] = (("24h", 24 * 60), ("2h", 2 * 60))


class ReminderScheduler:
    """Builds and stores the reminders for an appointment (future ones only)."""

    def __init__(self, store: ReminderStore, ids: IdGenerator, clock: Clock) -> None:
        self._store = store
        self._ids = ids
        self._clock = clock

    async def schedule_for(self, appointment: Appointment) -> None:
        now = self._clock.now()
        reminders = [
            Reminder(
                ReminderId(self._ids.new()),
                appointment.business_id,
                appointment.id,
                appointment.slot.starts_at - timedelta(minutes=minutes),
                kind,
            )
            for kind, minutes in REMINDER_OFFSETS
            if appointment.slot.starts_at - timedelta(minutes=minutes) > now
        ]
        if reminders:
            await self._store.schedule(reminders)

    async def reschedule_for(self, appointment: Appointment) -> None:
        await self._store.cancel_for(appointment.id)
        await self.schedule_for(appointment)


class BookAppointment:
    def __init__(
        self, calendar: Calendar, scheduler: ReminderScheduler, events: EventPublisher
    ) -> None:
        self._calendar = calendar
        self._scheduler = scheduler
        self._events = events

    async def __call__(
        self,
        service: Service,
        resource_id: ResourceId,
        customer: Customer,
        slot: TimeSlot,
        intake: tuple[IntakeAnswer, ...] = (),
    ) -> Appointment:
        appointment = await self._calendar.book(service, resource_id, customer, slot, intake)
        await self._scheduler.schedule_for(appointment)
        await self._events.publish(AppointmentBooked(appointment.business_id, appointment.id))
        return appointment


class RescheduleAppointment:
    def __init__(self, calendar: Calendar, scheduler: ReminderScheduler) -> None:
        self._calendar = calendar
        self._scheduler = scheduler

    async def __call__(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment:
        moved = await self._calendar.move(appointment_id, slot)
        await self._scheduler.reschedule_for(moved)
        return moved


class CancelAppointment:
    def __init__(self, calendar: Calendar, store: ReminderStore, events: EventPublisher) -> None:
        self._calendar = calendar
        self._store = store
        self._events = events

    async def __call__(self, appointment_id: AppointmentId) -> Appointment:
        cancelled = await self._calendar.cancel(appointment_id)
        await self._store.cancel_for(appointment_id)
        await self._events.publish(AppointmentCancelled(cancelled.business_id, appointment_id))
        return cancelled


class ConfirmAppointment:
    """Owner-driven transition: pending → confirmed, scoped to the owner's business."""

    def __init__(
        self,
        appointments: AppointmentRepository,
        calendar: Calendar,
        events: EventPublisher,
    ) -> None:
        self._appointments = appointments
        self._calendar = calendar
        self._events = events

    async def __call__(self, business_id: BusinessId, appointment_id: AppointmentId) -> Appointment:
        appointment = await self._appointments.get(appointment_id)
        if appointment.business_id != business_id:
            raise TenantMismatch("appointment belongs to another business")
        confirmed = await self._calendar.confirm(appointment_id)
        await self._events.publish(AppointmentConfirmed(confirmed.business_id, appointment_id))
        return confirmed
