"""The appointment and reminder state machines — valid and rejected moves."""

import pytest

from frontdesk.domain.enums import AppointmentStatus as A
from frontdesk.domain.enums import ReminderStatus as R
from frontdesk.domain.errors import InvalidTransition
from frontdesk.domain.transitions import AppointmentEvent as AE
from frontdesk.domain.transitions import ReminderEvent as RE
from frontdesk.domain.transitions import next_appointment_status, next_reminder_status


@pytest.mark.parametrize(
    ("status", "event", "expected"),
    [
        (A.PENDING, AE.CONFIRM, A.CONFIRMED),
        (A.PENDING, AE.RESCHEDULE, A.PENDING),
        (A.CONFIRMED, AE.RESCHEDULE, A.CONFIRMED),
        (A.PENDING, AE.CANCEL, A.CANCELLED),
        (A.CONFIRMED, AE.CANCEL, A.CANCELLED),
        (A.CONFIRMED, AE.COMPLETE, A.COMPLETED),
        (A.CONFIRMED, AE.MARK_NO_SHOW, A.NO_SHOW),
    ],
)
def test_appointment_valid_transitions(status: A, event: AE, expected: A) -> None:
    assert next_appointment_status(status, event) == expected


@pytest.mark.parametrize(
    ("status", "event"),
    [
        (A.PENDING, AE.COMPLETE),
        (A.PENDING, AE.MARK_NO_SHOW),
        (A.CANCELLED, AE.CONFIRM),
        (A.COMPLETED, AE.CANCEL),
        (A.NO_SHOW, AE.RESCHEDULE),
        (A.CONFIRMED, AE.CONFIRM),
    ],
)
def test_appointment_rejected_transitions(status: A, event: AE) -> None:
    with pytest.raises(InvalidTransition):
        next_appointment_status(status, event)


@pytest.mark.parametrize(
    ("status", "event", "expected"),
    [(R.PENDING, RE.SEND, R.SENT), (R.PENDING, RE.CANCEL, R.CANCELLED)],
)
def test_reminder_valid_transitions(status: R, event: RE, expected: R) -> None:
    assert next_reminder_status(status, event) == expected


@pytest.mark.parametrize(
    ("status", "event"),
    [(R.SENT, RE.SEND), (R.SENT, RE.CANCEL), (R.CANCELLED, RE.SEND), (R.CANCELLED, RE.CANCEL)],
)
def test_reminder_rejected_transitions(status: R, event: RE) -> None:
    with pytest.raises(InvalidTransition):
        next_reminder_status(status, event)
