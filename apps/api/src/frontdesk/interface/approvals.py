"""The approvals inbox API: list a business's Airlock approval requests and decide them.

Scoped per tenant and behind the owner guard — an owner only ever sees and decides their
own business's pending sensitive actions.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.ports import ApprovalStore

Guard = Callable[..., Awaitable[None]] | None


class ApprovalView(BaseModel):
    id: str
    summary: str
    tool: str
    args: dict[str, object]
    risk: str  # airlock RiskTier (e.g. "sensitive")


class DecisionInput(BaseModel):
    approved: bool


def build_approvals_router(store: ApprovalStore, guard: Guard = None) -> APIRouter:
    # The guard scopes the path business_id to the authenticated owner.
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/approvals")
    async def list_approvals(business_id: str) -> list[ApprovalView]:
        return [
            ApprovalView(
                id=record.request_id,
                summary=record.summary,
                tool=record.tool,
                args=record.args,
                risk=record.risk,
            )
            for record in await store.pending(business_id)
        ]

    @router.post("/api/businesses/{business_id}/approvals/{request_id}")
    async def decide(business_id: str, request_id: str, body: DecisionInput) -> dict[str, str]:
        record = await store.decide(request_id, business_id, approved=body.approved)
        if record is None:
            raise HTTPException(status_code=404, detail="approval not found")
        return {"status": record.status}

    return router
