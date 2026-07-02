"""Admin management of premium-feature entitlements (Phase 3, ADR-0013).

Unlike the read-only analytics admin surface (ADR-0012), these routes WRITE per-tenant state — an
operator approves or suspends a business's premium feature. They sit behind the admin guard.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.entitlements import ReviewFeatureRequest
from frontdesk.application.ports import EntitlementDirectory
from frontdesk.domain.entitlements import Entitlement
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, FeatureKey

Guard = Callable[..., Awaitable[None]] | None


class EntitlementView(BaseModel):
    business_id: str
    feature_key: str
    status: str
    requested_at: str
    decided_at: str | None


class DecisionBody(BaseModel):
    status: Literal["active", "suspended"]  # approve or suspend; other values → 422


def _view(entitlement: Entitlement) -> EntitlementView:
    return EntitlementView(
        business_id=entitlement.business_id,
        feature_key=entitlement.feature_key,
        status=entitlement.status.value,
        requested_at=entitlement.requested_at.isoformat(),
        decided_at=entitlement.decided_at.isoformat() if entitlement.decided_at else None,
    )


def build_admin_entitlements_router(
    directory: EntitlementDirectory, review: ReviewFeatureRequest, guard: Guard = None
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/admin/entitlements")
    async def pending_requests() -> list[EntitlementView]:
        return [_view(entitlement) for entitlement in await directory.pending()]

    @router.get("/api/admin/businesses/{business_id}/features")
    async def business_features(business_id: str) -> list[EntitlementView]:
        held = await directory.for_business(BusinessId(business_id))
        return [_view(entitlement) for entitlement in held]

    @router.put("/api/admin/businesses/{business_id}/features/{feature_key}")
    async def decide(business_id: str, feature_key: str, body: DecisionBody) -> EntitlementView:
        business = BusinessId(business_id)
        key = FeatureKey(feature_key)
        try:
            entitlement = (
                await review.approve(business, key)
                if body.status == "active"
                else await review.suspend(business, key)
            )
        except UnknownFeature as exc:
            raise HTTPException(404, "unknown feature") from exc
        return _view(entitlement)

    return router
