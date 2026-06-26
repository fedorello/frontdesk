"""Usage / billing-seam endpoint (M6): today's managed-default usage per business."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from frontdesk.application.ports import Clock, UsageStore
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId

Guard = Callable[..., Awaitable[None]] | None


class UsageView(BaseModel):
    day: str
    used: int
    limit: int  # 0 = unlimited


def build_metrics_router(
    usage: UsageStore,
    settings: Settings,
    clock: Clock,
    guard: Guard = None,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/usage")
    async def usage_today(business_id: str) -> UsageView:
        day = clock.now().date().isoformat()
        used = await usage.count(BusinessId(business_id), day)
        return UsageView(day=day, used=used, limit=settings.managed_default_daily_limit)

    return router
