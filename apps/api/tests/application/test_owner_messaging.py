"""Owner takeover: sending a reply relays + records + mutes the AI; handoff toggles it back."""

import pytest

from frontdesk.application.owner_actions import OwnerSendMessage, SetConversationHandoff
from frontdesk.domain.enums import Channel, MessageRole
from frontdesk.domain.errors import TenantMismatch
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Business, Customer
from tests.application.world import World, build_world


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[Customer, str]] = []

    async def notify(self, business: Business, customer: Customer, text: str) -> None:
        self.sent.append((customer, text))


def _send(world: World, notifier: FakeNotifier) -> OwnerSendMessage:
    deps = world.deps
    return OwnerSendMessage(
        deps.customers, deps.businesses, deps.conversations, notifier, world.clock
    )


async def test_owner_send_relays_with_label_records_owner_message_and_takes_over() -> None:
    world = build_world([])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    notifier = FakeNotifier()

    await _send(world, notifier)(world.business.id, customer.id, "On my way!")

    # Relayed under the owner label (no name set → the localized default), with the text.
    assert len(notifier.sent) == 1
    assert notifier.sent[-1][1] == "[Staff]: On my way!"
    # Recorded as an OWNER turn.
    history = await world.deps.conversations.history(customer)
    assert history[-1].role == MessageRole.OWNER
    assert history[-1].text == "On my way!"
    # The owner now owns the conversation.
    assert (await world.deps.customers.get(customer.id)).handled_by_owner is True


async def test_owner_send_refuses_another_business() -> None:
    world = build_world([])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")

    with pytest.raises(TenantMismatch):
        await _send(world, FakeNotifier())(BusinessId("someone-else"), customer.id, "hi")


async def test_handoff_hands_back_to_the_assistant() -> None:
    world = build_world([])
    customer = await world.customers.upsert(world.business.id, Channel.WHATSAPP, "+C")
    await world.deps.customers.set_handled(customer.id, True)

    await SetConversationHandoff(world.deps.customers)(world.business.id, customer.id, False)

    assert (await world.deps.customers.get(customer.id)).handled_by_owner is False


async def test_handoff_unknown_customer_raises() -> None:
    world = build_world([])
    with pytest.raises(KeyError):
        await SetConversationHandoff(world.deps.customers)(
            world.business.id, CustomerId("ghost"), True
        )
