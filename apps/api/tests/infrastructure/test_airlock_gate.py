"""The Airlock-backed approval gate holds sensitive actions and queues them per tenant."""

from frontdesk.application.ports import SensitiveAction
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, InMemoryApprovalStore


async def test_gate_holds_sensitive_action_and_queues_it() -> None:
    store = InMemoryApprovalStore()
    gate = AirlockApprovalGate(store)

    decision = await gate.guard(
        SensitiveAction("biz-1", "issue_refund", {"appointment_id": "ap-1"}, "Refund for ap-1")
    )

    assert decision.approved is False
    queue = await store.pending("biz-1")
    assert len(queue) == 1
    assert queue[0].tool == "issue_refund"
    assert queue[0].risk == "sensitive"  # airlock RiskTier
    assert queue[0].args == {"appointment_id": "ap-1"}


async def test_decide_resolves_a_pending_approval() -> None:
    store = InMemoryApprovalStore()
    await AirlockApprovalGate(store).guard(SensitiveAction("biz-1", "issue_refund", {}, "Refund"))

    request_id = (await store.pending("biz-1"))[0].request_id
    record = await store.decide(request_id, "biz-1", approved=True)

    assert record is not None
    assert record.status == "approved"
    assert await store.pending("biz-1") == []  # no longer awaiting
    assert await store.decide("unknown", "biz-1", approved=True) is None


async def test_approvals_are_scoped_to_their_tenant() -> None:
    store = InMemoryApprovalStore()
    gate = AirlockApprovalGate(store)
    await gate.guard(SensitiveAction("biz-1", "issue_refund", {}, "A's refund"))

    request_id = (await store.pending("biz-1"))[0].request_id

    # Another business neither sees nor can decide biz-1's approval.
    assert await store.pending("biz-2") == []
    assert await store.decide(request_id, "biz-2", approved=True) is None
    assert (await store.pending("biz-1"))[0].status == "pending"  # untouched by biz-2
