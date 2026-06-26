"""The Airlock-backed approval gate holds sensitive actions and queues them."""

from frontdesk.application.ports import SensitiveAction
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals


async def test_gate_holds_sensitive_action_and_queues_it() -> None:
    pending = PendingApprovals()
    gate = AirlockApprovalGate(pending)

    decision = await gate.guard(
        SensitiveAction("issue_refund", {"appointment_id": "ap-1"}, "Refund for ap-1")
    )

    assert decision.approved is False
    queue = pending.pending()
    assert len(queue) == 1
    assert queue[0].request.tool_call.name == "issue_refund"
    assert queue[0].request.risk.value == "sensitive"  # airlock RiskTier


async def test_decide_resolves_a_pending_approval() -> None:
    pending = PendingApprovals()
    await AirlockApprovalGate(pending).guard(SensitiveAction("issue_refund", {}, "Refund"))

    request_id = str(pending.pending()[0].request.request_id)
    item = pending.decide(request_id, approved=True)

    assert item is not None
    assert item.status == "approved"
    assert pending.pending() == []  # no longer awaiting
    assert pending.decide("unknown", approved=True) is None
