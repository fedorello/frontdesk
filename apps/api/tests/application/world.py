"""A wired-up world of fakes for the application tests (not collected by pytest)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import (
    AvailabilityClaimDetector,
    Completion,
    InboundMessage,
)
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId, ResourceId, ServiceId
from frontdesk.domain.models import (
    Business,
    Customer,
    IntakeField,
    KnowledgeItem,
    Resource,
    Service,
    WorkingHours,
)
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

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)  # Friday, 12:00 UTC
BIZ_ADDR = "+BIZ"
CUST_ADDR = "+CUST"


@dataclass
class World:
    assistant: Assistant
    messaging: InMemoryMessaging
    events: InMemoryEventPublisher
    appointments: InMemoryAppointmentRepository
    reminders: InMemoryReminderStore
    customers: InMemoryCustomerRepository
    services: InMemoryServiceRepository
    business: Business
    service: Service
    calendar: InMemoryCalendar
    book: BookAppointment
    reschedule: RescheduleAppointment
    cancel: CancelAppointment
    clock: FixedClock
    deps: AssistantDeps


def build_world(
    script: Sequence[Completion],
    *,
    gate_approves: bool = False,
    intake_fields: tuple[IntakeField, ...] = (),
    requires_confirmation: bool = False,
    detector: AvailabilityClaimDetector | None = None,
) -> World:
    business = Business(
        BusinessId("biz"),
        "Ana's Studio",
        "UTC",
        lead_time_minutes=0,
        buffer_minutes=0,
        knowledge=(KnowledgeItem("What are your hours?", "We're open 9 to 17, Monday to Friday."),),
    )
    resource = Resource(
        ResourceId("res"),
        BusinessId("biz"),
        "Ana",
        tuple(WorkingHours(day, time(9), time(17)) for day in range(7)),
    )
    service = Service(
        ServiceId("svc"),
        BusinessId("biz"),
        "Haircut",
        60,
        resource_ids=(ResourceId("res"),),  # the group "res" owns the schedule
        intake_fields=intake_fields,
        requires_confirmation=requires_confirmation,
    )

    clock = FixedClock(NOW)
    appointments = InMemoryAppointmentRepository()
    services = InMemoryServiceRepository([service])
    calendar = InMemoryCalendar(
        business, [resource], clock, SequentialIdGenerator("ap"), appointments, services
    )
    reminders = InMemoryReminderStore()
    scheduler = ReminderScheduler(reminders, SequentialIdGenerator("rem"), clock)
    events = InMemoryEventPublisher()
    messaging = InMemoryMessaging()
    customers = InMemoryCustomerRepository(SequentialIdGenerator("cus"))

    book = BookAppointment(calendar, scheduler, events)
    reschedule = RescheduleAppointment(calendar, scheduler)
    cancel = CancelAppointment(calendar, reminders, events)

    deps = AssistantDeps(
        llm=ScriptedLlmProvider(script),
        businesses=InMemoryBusinessRepository(
            [business], {(Channel.WHATSAPP, BIZ_ADDR): business.id}
        ),
        customers=customers,
        conversations=InMemoryConversationRepository(),
        services=services,
        appointments=appointments,
        calendar=calendar,
        book=book,
        reschedule=reschedule,
        cancel=cancel,
        messaging=messaging,
        events=events,
        gate=AutoDecisionGate(approved=gate_approves),
        clock=clock,
        detector=detector or InMemoryAvailabilityClaimDetector(),
    )
    return World(
        assistant=Assistant(deps),
        messaging=messaging,
        events=events,
        appointments=appointments,
        reminders=reminders,
        customers=customers,
        services=services,
        business=business,
        service=service,
        calendar=calendar,
        book=book,
        reschedule=reschedule,
        cancel=cancel,
        clock=clock,
        deps=deps,
    )


def make_customer() -> Customer:
    return Customer(CustomerId("cus-1"), BusinessId("biz"), Channel.WHATSAPP, CUST_ADDR)


def inbound(text: str) -> InboundMessage:
    return InboundMessage(Channel.WHATSAPP, CUST_ADDR, BIZ_ADDR, text, NOW, "pm-1")
