"""The approvals inbox API lists a tenant's Airlock requests and records decisions."""

import httpx
from fastapi import FastAPI

from frontdesk.application.ports import SensitiveAction
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, InMemoryApprovalStore
from frontdesk.interface.approvals import build_approvals_router


def _client(store: InMemoryApprovalStore) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(build_approvals_router(store))  # no guard in the unit (tests scoping)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_lists_and_decides_only_its_own_business_approvals() -> None:
    store = InMemoryApprovalStore()
    await AirlockApprovalGate(store).guard(
        SensitiveAction("biz-1", "issue_refund", {"appointment_id": "ap-1"}, "Refund for +1")
    )

    async with _client(store) as client:
        listed = (await client.get("/api/businesses/biz-1/approvals")).json()
        assert len(listed) == 1
        assert listed[0]["tool"] == "issue_refund"

        # Another tenant sees none of biz-1's approvals and can't decide them.
        assert (await client.get("/api/businesses/biz-2/approvals")).json() == []
        request_id = listed[0]["id"]
        foreign = await client.post(
            f"/api/businesses/biz-2/approvals/{request_id}", json={"approved": True}
        )
        assert foreign.status_code == 404  # scoped out

        decided = await client.post(
            f"/api/businesses/biz-1/approvals/{request_id}", json={"approved": True}
        )
        assert decided.status_code == 200
        assert decided.json()["status"] == "approved"

        assert (await client.get("/api/businesses/biz-1/approvals")).json() == []
        missing = await client.post("/api/businesses/biz-1/approvals/nope", json={"approved": True})
        assert missing.status_code == 404
