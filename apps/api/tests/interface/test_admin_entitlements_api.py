"""Admin entitlement-management endpoints (Phase 3, ADR-0013), against in-memory fakes.

The guard is None here so we test the handlers; the admin guard is exercised in test_admin_guard.
"""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.entitlements import ReviewFeatureRequest
from frontdesk.domain.entitlements import Entitlement, FeatureRegistry, PremiumFeature
from frontdesk.domain.ids import BusinessId, FeatureKey
from frontdesk.infrastructure.memory import InMemoryEntitlementRepository
from frontdesk.infrastructure.system import FixedClock
from frontdesk.interface.admin_entitlements_api import build_admin_entitlements_router

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")
BIZ = BusinessId("biz")


def _client(*entitlements: Entitlement) -> httpx.AsyncClient:
    registry = FeatureRegistry([PremiumFeature(VOICE, "Voice", "Answers calls.", "$1 per call")])
    repo = InMemoryEntitlementRepository(entitlements)
    app = FastAPI()
    app.include_router(
        build_admin_entitlements_router(repo, ReviewFeatureRequest(registry, repo, FixedClock(NOW)))
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_lists_pending_requests() -> None:
    async with _client(Entitlement.requested(BIZ, VOICE, NOW)) as client:
        response = await client.get("/api/admin/entitlements")

    assert response.status_code == 200
    assert [(e["business_id"], e["status"]) for e in response.json()] == [("biz", "requested")]


async def test_approve_activates_the_feature() -> None:
    async with _client(Entitlement.requested(BIZ, VOICE, NOW)) as client:
        response = await client.put(
            "/api/admin/businesses/biz/features/voice_receptionist", json={"status": "active"}
        )
        listed = await client.get("/api/admin/businesses/biz/features")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert listed.json()[0]["status"] == "active"


async def test_suspend_turns_the_feature_off() -> None:
    async with _client(Entitlement.requested(BIZ, VOICE, NOW).approve(NOW)) as client:
        response = await client.put(
            "/api/admin/businesses/biz/features/voice_receptionist", json={"status": "suspended"}
        )

    assert response.json()["status"] == "suspended"


async def test_decide_unknown_feature_is_404() -> None:
    async with _client() as client:
        response = await client.put(
            "/api/admin/businesses/biz/features/ghost", json={"status": "active"}
        )

    assert response.status_code == 404


async def test_decide_rejects_an_invalid_status() -> None:
    async with _client() as client:
        response = await client.put(
            "/api/admin/businesses/biz/features/voice_receptionist", json={"status": "maybe"}
        )

    assert response.status_code == 422  # only active|suspended are allowed
