"""Owner-facing premium-feature catalog + self-serve request (Phase 2).

Both routes are business-scoped and sit behind the owner guard (the token must own the path's
business). ``GET`` lists the catalog with this business's status; ``POST .../request`` records a
request (idempotent) that an operator later approves.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.entitlements import FeatureCatalog, FeatureView, RequestFeature
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, FeatureKey

Guard = Callable[..., Awaitable[None]] | None


class FeatureCatalogItem(BaseModel):
    key: str
    name: str
    description: str
    pricing: str
    status: str | None  # requested | active | suspended, or null when never requested


def _item(view: FeatureView) -> FeatureCatalogItem:
    return FeatureCatalogItem(
        key=view.key,
        name=view.name,
        description=view.description,
        pricing=view.pricing,
        status=view.status.value if view.status is not None else None,
    )


def build_features_router(
    catalog: FeatureCatalog, requests: RequestFeature, guard: Guard = None
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/features")
    async def list_features(business_id: str) -> list[FeatureCatalogItem]:
        views = await catalog.for_business(BusinessId(business_id))
        return [_item(view) for view in views]

    @router.post("/api/businesses/{business_id}/features/{feature_key}/request")
    async def request_feature(business_id: str, feature_key: str) -> FeatureCatalogItem:
        business = BusinessId(business_id)
        try:
            await requests.execute(business, FeatureKey(feature_key))
        except UnknownFeature as exc:
            raise HTTPException(404, "unknown feature") from exc
        views = await catalog.for_business(business)
        return next(_item(view) for view in views if view.key == feature_key)

    return router
