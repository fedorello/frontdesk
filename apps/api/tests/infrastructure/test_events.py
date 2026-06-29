"""The dispatching event publisher fans out to listeners and isolates their failures."""

from frontdesk.application.ports import (
    AppointmentBooked,
    DomainEvent,
    MessageReceived,
)
from frontdesk.domain.ids import AppointmentId, BusinessId, CustomerId
from frontdesk.infrastructure.events import DispatchingEventPublisher, LoggingEventListener

_EVENT = AppointmentBooked(BusinessId("biz"), AppointmentId("ap"))


class _RecordingListener:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def on_event(self, event: DomainEvent) -> None:
        self.events.append(event)


class _FailingListener:
    async def on_event(self, event: DomainEvent) -> None:
        raise RuntimeError("boom")


async def test_dispatches_to_every_listener() -> None:
    first, second = _RecordingListener(), _RecordingListener()

    await DispatchingEventPublisher([first, second]).publish(_EVENT)

    assert first.events == [_EVENT]
    assert second.events == [_EVENT]


async def test_one_listener_failing_does_not_stop_the_others() -> None:
    recording = _RecordingListener()

    # The failing listener is logged and skipped; the recorder still runs.
    await DispatchingEventPublisher([_FailingListener(), recording]).publish(_EVENT)

    assert recording.events == [_EVENT]


async def test_logging_event_listener_accepts_any_event() -> None:
    await LoggingEventListener().on_event(MessageReceived(BusinessId("b"), CustomerId("c"), "hi"))
