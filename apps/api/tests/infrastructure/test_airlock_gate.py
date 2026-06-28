"""The Airlock-backed approval gate holds sensitive actions and queues them per tenant."""

from frontdesk.application.ports import SensitiveAction
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals


async def test_gate_holds_sensitive_action_and_queues_it() -> None:
    pending = PendingApprovals()
    gate = AirlockApprovalGate(pending)

    decision = await gate.guard(
        SensitiveAction("biz-1", "issue_refund", {"appointment_id": "ap-1"}, "Refund for ap-1")
    )

    assert decision.approved is False
    queue = pending.pending("biz-1")
    assert len(queue) == 1
    assert queue[0].request.tool_call.name == "issue_refund"
    assert queue[0].request.risk.value == "sensitive"  # airlock RiskTier


async def test_decide_resolves_a_pending_approval() -> None:
    pending = PendingApprovals()
    await AirlockApprovalGate(pending).guard(SensitiveAction("biz-1", "issue_refund", {}, "Refund"))

    request_id = str(pending.pending("biz-1")[0].request.request_id)
    item = pending.decide(request_id, "biz-1", approved=True)

    assert item is not None
    assert item.status == "approved"
    assert pending.pending("biz-1") == []  # no longer awaiting
    assert pending.decide("unknown", "biz-1", approved=True) is None


async def test_approvals_are_scoped_to_their_tenant() -> None:
    pending = PendingApprovals()
    gate = AirlockApprovalGate(pending)
    await gate.guard(SensitiveAction("biz-1", "issue_refund", {}, "A's refund"))

    request_id = str(pending.pending("biz-1")[0].request.request_id)

    # Another business neither sees nor can decide biz-1's approval.
    assert pending.pending("biz-2") == []
    assert pending.decide(request_id, "biz-2", approved=True) is None
    assert pending.pending("biz-1")[0].status == "pending"  # untouched by biz-2
