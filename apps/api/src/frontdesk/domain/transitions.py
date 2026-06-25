"""The appointment and reminder state machines (pure)."""

from enum import StrEnum

from .enums import AppointmentStatus, ReminderStatus
from .errors import InvalidTransition


class AppointmentEvent(StrEnum):
    CONFIRM = "confirm"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    COMPLETE = "complete"
    MARK_NO_SHOW = "mark_no_show"


class ReminderEvent(StrEnum):
    SEND = "send"
    CANCEL = "cancel"


_APPOINTMENT: dict[tuple[AppointmentStatus, AppointmentEvent], AppointmentStatus] = {
    (AppointmentStatus.PENDING, AppointmentEvent.CONFIRM): AppointmentStatus.CONFIRMED,
    (AppointmentStatus.PENDING, AppointmentEvent.RESCHEDULE): AppointmentStatus.PENDING,
    (AppointmentStatus.CONFIRMED, AppointmentEvent.RESCHEDULE): AppointmentStatus.CONFIRMED,
    (AppointmentStatus.PENDING, AppointmentEvent.CANCEL): AppointmentStatus.CANCELLED,
    (AppointmentStatus.CONFIRMED, AppointmentEvent.CANCEL): AppointmentStatus.CANCELLED,
    (AppointmentStatus.CONFIRMED, AppointmentEvent.COMPLETE): AppointmentStatus.COMPLETED,
    (AppointmentStatus.CONFIRMED, AppointmentEvent.MARK_NO_SHOW): AppointmentStatus.NO_SHOW,
}

_REMINDER: dict[tuple[ReminderStatus, ReminderEvent], ReminderStatus] = {
    (ReminderStatus.PENDING, ReminderEvent.SEND): ReminderStatus.SENT,
    (ReminderStatus.PENDING, ReminderEvent.CANCEL): ReminderStatus.CANCELLED,
}


def next_appointment_status(
    status: AppointmentStatus, event: AppointmentEvent
) -> AppointmentStatus:
    """The status after applying ``event``, or raise ``InvalidTransition``."""
    try:
        return _APPOINTMENT[(status, event)]
    except KeyError:
        raise InvalidTransition(f"cannot {event} an appointment that is {status}") from None


def next_reminder_status(status: ReminderStatus, event: ReminderEvent) -> ReminderStatus:
    """The status after applying ``event``, or raise ``InvalidTransition``."""
    try:
        return _REMINDER[(status, event)]
    except KeyError:
        raise InvalidTransition(f"cannot {event} a reminder that is {status}") from None
