"""Account lifecycle: permanently delete a business and all of its data."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, Response

from frontdesk.application.ports import BusinessEraser
from frontdesk.domain.ids import BusinessId

Guard = Callable[..., Awaitable[None]] | None

_NO_CONTENT = 204


def build_account_router(eraser: BusinessEraser, guard: Guard = None) -> APIRouter:
    # The guard scopes the path's business_id to the authenticated owner, so this only
    # ever erases the caller's own business.
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.delete("/api/businesses/{business_id}", status_code=_NO_CONTENT)
    async def delete_account(business_id: str) -> Response:
        await eraser.erase(BusinessId(business_id))
        return Response(status_code=_NO_CONTENT)

    return router
