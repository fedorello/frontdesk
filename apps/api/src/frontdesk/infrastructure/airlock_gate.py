"""The approval gate, backed by the published ``airlock-hitl`` package (ADR-0005).

Frontdesk dogfoods Airlock: a sensitive tool call is turned into an Airlock
``Tool``/``ToolCall`` and run through Airlock's ``RiskBasedGatePolicy``. When the policy
says it needs a human, we persist an ``ApprovalRecord`` to the ``ApprovalStore`` and hold
the action — the dashboard approvals inbox reads these (per tenant) and a human decides.
"""

import uuid
from collections.abc import Mapping
from dataclasses import replace

from airlock import (
    RiskBasedGatePolicy,
    RiskTier,
    RunState,
    RunStatus,
    Tool,
    ToolCall,
)
from airlock.application.ports.gate_policy import GateDecisionInput
from airlock.domain.identifiers import RunId, ToolCallId

from frontdesk.application.ports import (
    ApprovalRecord,
    ApprovalStore,
    Decision,
    SensitiveAction,
)


async def _never_runs(_args: Mapping[str, object]) -> object:
    # The gate only inspects risk; the real effect lives in the use case.
    raise RuntimeError("gate handler must never execute")


class InMemoryApprovalStore:
    """A per-process approval queue (the ``ApprovalStore`` port) for tests and local dev."""

    def __init__(self) -> None:
        self._items: dict[str, ApprovalRecord] = {}

    async def add(self, record: ApprovalRecord) -> None:
        self._items[record.request_id] = record

    async def pending(self, business_id: str) -> list[ApprovalRecord]:
        return [
            r
            for r in self._items.values()
            if r.status == "pending" and r.business_id == business_id
        ]

    async def decide(
        self, request_id: str, business_id: str, *, approved: bool
    ) -> ApprovalRecord | None:
        record = self._items.get(request_id)
        # Scoped to the tenant: an owner can only decide their own business's approvals.
        if record is None or record.business_id != business_id:
            return None
        record = replace(record, status="approved" if approved else "rejected")
        self._items[request_id] = record
        return record


class AirlockApprovalGate:
    """Implements the ApprovalGate port using Airlock's gate policy and types."""

    def __init__(self, store: ApprovalStore) -> None:
        self._policy = RiskBasedGatePolicy()
        self._store = store

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

        await self._store.add(
            ApprovalRecord(
                request_id=uuid.uuid4().hex,
                business_id=action.business_id,
                tool=action.tool_name,
                summary=action.summary,
                risk=RiskTier.SENSITIVE.value,
                args=dict(action.args),
            )
        )
        return Decision(approved=False)
