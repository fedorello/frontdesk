"""The approvals inbox API lists Airlock requests and records decisions."""

import httpx
from fastapi import FastAPI

from frontdesk.application.ports import SensitiveAction
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals
from frontdesk.interface.approvals import build_approvals_router


def _client(pending: PendingApprovals) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(build_approvals_router(pending))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_lists_and_decides_approvals() -> None:
    pending = PendingApprovals()
    await AirlockApprovalGate(pending).guard(
        SensitiveAction("issue_refund", {"appointment_id": "ap-1"}, "Refund for +1")
    )

    async with _client(pending) as client:
        listed = (await client.get("/api/approvals")).json()
        assert len(listed) == 1
        assert listed[0]["tool"] == "issue_refund"

        decided = await client.post(f"/api/approvals/{listed[0]['id']}", json={"approved": True})
        assert decided.status_code == 200
        assert decided.json()["status"] == "approved"

        assert (await client.get("/api/approvals")).json() == []
        missing = await client.post("/api/approvals/nope", json={"approved": True})
        assert missing.status_code == 404
