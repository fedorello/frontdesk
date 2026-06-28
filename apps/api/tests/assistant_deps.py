"""Shared builder for a fully in-memory AssistantDeps — reused by the transport tests."""

from datetime import time

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import AssistantDeps
from frontdesk.domain.ids import BusinessId, ResourceId
from frontdesk.domain.models import Business, Resource, WorkingHours
from frontdesk.infrastructure.memory import (
    AutoDecisionGate,
    InMemoryAppointmentRepository,
    InMemoryAvailabilityClaimDetector,
    InMemoryBusinessRepository,
    InMemoryCalendar,
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryEventPublisher,
    InMemoryMessaging,
    InMemoryReminderStore,
    InMemoryServiceRepository,
    ScriptedLlmProvider,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from tests.port_contracts import NOW


def build_assistant_deps(businesses: InMemoryBusinessRepository) -> AssistantDeps:
    """An in-memory AssistantDeps; ``llm`` and ``messaging`` are replaced per business."""
    business = Business(BusinessId("biz1"), "Ana", "UTC")
    resource = Resource(
        ResourceId("res"), BusinessId("biz1"), "Ana", (WorkingHours(0, time(9), time(17)),)
    )
    clock = FixedClock(NOW)
    appointments = InMemoryAppointmentRepository()
    services = InMemoryServiceRepository([])
    calendar = InMemoryCalendar(
        business, [resource], clock, SequentialIdGenerator("ap"), appointments, services
    )
    reminders = InMemoryReminderStore()
    scheduler = ReminderScheduler(reminders, SequentialIdGenerator("rem"), clock)
    events = InMemoryEventPublisher()
    return AssistantDeps(
        llm=ScriptedLlmProvider([]),
        businesses=businesses,
        customers=InMemoryCustomerRepository(SequentialIdGenerator("cus")),
        conversations=InMemoryConversationRepository(),
        services=services,
        appointments=appointments,
        calendar=calendar,
        book=BookAppointment(calendar, scheduler, events),
        reschedule=RescheduleAppointment(calendar, scheduler),
        cancel=CancelAppointment(calendar, reminders, events),
        messaging=InMemoryMessaging(),
        events=events,
        gate=AutoDecisionGate(approved=False),
        clock=clock,
        detector=InMemoryAvailabilityClaimDetector(),
    )
