"""The approval gate, backed by the published ``airlock-hitl`` package (ADR-0005).

Frontdesk dogfoods Airlock: a sensitive tool call is turned into an Airlock
``Tool``/``ToolCall`` and run through Airlock's ``RiskBasedGatePolicy``. When the
policy says it needs a human, we raise an Airlock ``ApprovalRequest`` and hold the
action — the dashboard approvals inbox reads these and a human decides.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass

from airlock import (
    ApprovalRequest,
    RiskBasedGatePolicy,
    RiskTier,
    RunState,
    RunStatus,
    Tool,
    ToolCall,
)
from airlock.application.ports.gate_policy import GateDecisionInput
from airlock.domain.identifiers import RequestId, RunId, ToolCallId

from frontdesk.application.ports import Decision, SensitiveAction


async def _never_runs(_args: Mapping[str, object]) -> object:
    # The gate only inspects risk; the real effect lives in the use case.
    raise RuntimeError("gate handler must never execute")


@dataclass
class PendingApproval:
    request: ApprovalRequest
    summary: str
    business_id: str  # the tenant this approval belongs to
    status: str = "pending"  # pending | approved | rejected


class PendingApprovals:
    """The queue of Airlock approval requests awaiting a human, per business."""

    def __init__(self) -> None:
        self._items: dict[str, PendingApproval] = {}

    def add(self, request: ApprovalRequest, summary: str, business_id: str) -> None:
        self._items[str(request.request_id)] = PendingApproval(request, summary, business_id)

    def pending(self, business_id: str) -> list[PendingApproval]:
        return [
            item
            for item in self._items.values()
            if item.status == "pending" and item.business_id == business_id
        ]

    def decide(
        self, request_id: str, business_id: str, *, approved: bool
    ) -> PendingApproval | None:
        item = self._items.get(request_id)
        # Scoped to the tenant: an owner can only decide their own business's approvals.
        if item is None or item.business_id != business_id:
            return None
        item.status = "approved" if approved else "rejected"
        return item


class AirlockApprovalGate:
    """Implements the ApprovalGate port using Airlock's gate policy and types."""

    def __init__(self, pending: PendingApprovals) -> None:
        self._policy = RiskBasedGatePolicy()
        self._pending = pending

    async def guard(self, action: SensitiveAction) -> Decision:
        tool = Tool(
            name=action.tool_name,
            description=action.summary,
            parameters={},
            risk=RiskTier.SENSITIVE,
            handler=_never_runs,
        )
        call = ToolCall(
            id=ToolCallId(uuid.uuid4().hex), name=action.tool_name, args=dict(action.args)
        )
        state = RunState(
            run_id=RunId(uuid.uuid4().hex),
            status=RunStatus.AWAITING_APPROVAL,
            messages=[],
            pending_tool_calls=(),
            cursor=0,
            approval=None,
            metadata={},
        )
        if not self._policy.requires_approval(GateDecisionInput(tool, call, state)):
            return Decision(approved=True)

        request = ApprovalRequest(
            run_id=state.run_id,
            request_id=RequestId(uuid.uuid4().hex),
            tool_call=call,
            risk=RiskTier.SENSITIVE,
            context=dict(action.args),
        )
        self._pending.add(request, action.summary, action.business_id)
        return Decision(approved=False)
