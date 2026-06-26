"""The in-memory fakes satisfy the port contracts and behave correctly."""

from datetime import UTC, datetime

import pytest

from frontdesk.application.ports import (
    ApprovalGate,
    Clock,
    Completion,
    EventPublisher,
    IdGenerator,
    LlmProvider,
    MessageReceived,
    MessagingPort,
    OutboundMessage,
    SensitiveAction,
    ToolCall,
)
from frontdesk.domain.enums import MessageRole
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Message
from frontdesk.infrastructure.memory import (
    AutoDecisionGate,
    InMemoryAppointmentRepository,
    InMemoryBusinessRepository,
    InMemoryCalendar,
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryEventPublisher,
    InMemoryLlmConfigRepository,
    InMemoryMessaging,
    InMemoryReminderStore,
    InMemoryTelegramBotRepository,
    ScriptedLlmProvider,
)
from frontdesk.infrastructure.system import (
    FixedClock,
    SequentialIdGenerator,
    SystemClock,
    UuidIdGenerator,
)
from tests.port_contracts import (
    NOW,
    check_appointment_repository,
    check_business_repository,
    check_calendar,
    check_conversation_repository,
    check_customer_repository,
    check_llm_config_repository,
    check_reminder_store,
    check_telegram_bot_repository,
    make_business,
    make_customer,
    make_resource,
)

# --- The stateful fakes pass the shared port-contract suite ---


async def test_reminder_store_contract() -> None:
    await check_reminder_store(InMemoryReminderStore())


async def test_calendar_contract() -> None:
    store = InMemoryAppointmentRepository()
    calendar = InMemoryCalendar(
        make_business(), [make_resource()], FixedClock(NOW), SequentialIdGenerator(), store
    )
    await check_calendar(calendar)


async def test_business_repository_contract() -> None:
    from frontdesk.domain.enums import Channel

    repo = InMemoryBusinessRepository(
        [make_business()], {(Channel.WHATSAPP, "+100"): BusinessId("biz")}
    )
    await check_business_repository(repo)


async def test_customer_repository_contract() -> None:
    await check_customer_repository(InMemoryCustomerRepository(SequentialIdGenerator()))


async def test_conversation_repository_contract() -> None:
    await check_conversation_repository(InMemoryConversationRepository())


async def test_appointment_repository_contract() -> None:
    await check_appointment_repository(InMemoryAppointmentRepository())


# --- The simple fakes ---


async def test_messaging_records_sent() -> None:
    messaging: MessagingPort = InMemoryMessaging()
    await messaging.send(make_customer(), OutboundMessage("hi", buttons=("A", "B")))

    assert isinstance(messaging, InMemoryMessaging)
    assert messaging.sent[0][1].text == "hi"


async def test_event_publisher_records() -> None:
    publisher: EventPublisher = InMemoryEventPublisher()
    await publisher.publish(MessageReceived(BusinessId("biz"), CustomerId("c"), "hi"))

    assert isinstance(publisher, InMemoryEventPublisher)
    assert isinstance(publisher.events[0], MessageReceived)


async def test_scripted_llm_replays_then_raises() -> None:
    provider: LlmProvider = ScriptedLlmProvider(
        [
            Completion(None, (ToolCall("1", "book", {}),)),
            Completion("done"),
        ]
    )
    first = await provider.complete(system="s", messages=[], tools=[])
    second = await provider.complete(system="s", messages=[], tools=[])

    assert first.tool_calls[0].name == "book"
    assert second.text == "done"
    with pytest.raises(IndexError):
        await provider.complete(system="s", messages=[], tools=[])


def test_fixed_clock_is_frozen() -> None:
    clock: Clock = FixedClock(NOW)

    assert clock.now() == NOW


def test_system_clock_is_aware_utc() -> None:
    clock: Clock = SystemClock()
    now = clock.now()

    assert now.tzinfo == UTC
    assert isinstance(now, datetime)


def test_sequential_ids_increment() -> None:
    ids: IdGenerator = SequentialIdGenerator("x")

    assert (ids.new(), ids.new()) == ("x-1", "x-2")


def test_uuid_ids_are_distinct() -> None:
    ids: IdGenerator = UuidIdGenerator()

    assert ids.new() != ids.new()


async def test_auto_decision_gate() -> None:
    approve: ApprovalGate = AutoDecisionGate(approved=True)
    reject: ApprovalGate = AutoDecisionGate(approved=False)
    action = SensitiveAction("issue_refund", {}, "refund $50")

    assert (await approve.guard(action)).approved is True
    assert (await reject.guard(action)).approved is False


def test_message_role_used() -> None:
    # Exercise the Message DTO used across ports.
    assert Message(MessageRole.CUSTOMER, "hi", NOW).role is MessageRole.CUSTOMER


async def test_telegram_bot_repository_fake() -> None:
    await check_telegram_bot_repository(InMemoryTelegramBotRepository())


async def test_llm_config_repository_fake() -> None:
    await check_llm_config_repository(InMemoryLlmConfigRepository())
