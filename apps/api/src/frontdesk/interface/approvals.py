"""The approvals inbox API: list Airlock approval requests and decide them."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from frontdesk.infrastructure.airlock_gate import PendingApprovals


class ApprovalView(BaseModel):
    id: str
    summary: str
    tool: str
    args: dict[str, object]


class DecisionInput(BaseModel):
    approved: bool


def build_approvals_router(pending: PendingApprovals) -> APIRouter:
    router = APIRouter()

    @router.get("/api/approvals")
    async def list_approvals() -> list[ApprovalView]:
        return [
            ApprovalView(
                id=str(item.request.request_id),
                summary=item.summary,
                tool=item.request.tool_call.name,
                args=item.request.tool_call.args,
            )
            for item in pending.pending()
        ]

    @router.post("/api/approvals/{request_id}")
    async def decide(request_id: str, body: DecisionInput) -> dict[str, str]:
        item = pending.decide(request_id, approved=body.approved)
        if item is None:
            raise HTTPException(status_code=404, detail="approval not found")
        return {"status": item.status}

    return router
