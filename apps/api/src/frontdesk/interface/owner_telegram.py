"""Owner Telegram notifications API: confirm a linked chat, read status, toggle, unlink.

Every endpoint is owner-guarded (session → account → owns the business). Linking is *started*
from inside the bot (a /connect command), not here — the code must bind a real Telegram chat id.
See docs/OWNER_TELEGRAM_NOTIFICATIONS.md.
"""

from collections.abc import Awaitable, Callable
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.owner_linking import OwnerLinking
from frontdesk.application.ports import OwnerTelegramLinkRepository
from frontdesk.domain.errors import LinkCodeError
from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.notifications import LinkCodeProblem, OwnerTelegramLink

Guard = Callable[..., Awaitable[None]] | None

# Why a code can't be redeemed → HTTP status: unknown=404, used/expired=410 (gone), tenant=409.
_PROBLEM_STATUS = {
    LinkCodeProblem.NOT_FOUND: 404,
    LinkCodeProblem.USED: 410,
    LinkCodeProblem.EXPIRED: 410,
    LinkCodeProblem.WRONG_BUSINESS: 409,
}


class OwnerTelegramView(BaseModel):
    linked: bool
    telegram_name: str | None = None
    notifications_enabled: bool = False


class ConfirmInput(BaseModel):
    code: str


class NotificationsInput(BaseModel):
    enabled: bool


def _view(link: OwnerTelegramLink | None) -> OwnerTelegramView:
    if link is None:
        return OwnerTelegramView(linked=False)
    return OwnerTelegramView(
        linked=True,
        telegram_name=link.telegram_name,
        notifications_enabled=link.notifications_enabled,
    )


def build_owner_telegram_router(
    links: OwnerTelegramLinkRepository, linking: OwnerLinking, guard: Guard = None
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/telegram-owner")
    async def get_link(business_id: str) -> OwnerTelegramView:
        return _view(await links.get(BusinessId(business_id)))

    @router.post("/api/businesses/{business_id}/telegram-owner/confirm")
    async def confirm(business_id: str, body: ConfirmInput) -> OwnerTelegramView:
        try:
            link = await linking.confirm(BusinessId(business_id), LinkCode(body.code))
        except LinkCodeError as error:
            raise HTTPException(_PROBLEM_STATUS[error.problem], error.problem.value) from error
        return _view(link)

    @router.put("/api/businesses/{business_id}/telegram-owner/notifications")
    async def set_notifications(business_id: str, body: NotificationsInput) -> OwnerTelegramView:
        link = await links.get(BusinessId(business_id))
        if link is None:
            raise HTTPException(404, "no telegram linked")
        updated = replace(link, notifications_enabled=body.enabled)
        await links.upsert(updated)
        return _view(updated)

    @router.delete("/api/businesses/{business_id}/telegram-owner")
    async def unlink(business_id: str) -> OwnerTelegramView:
        await links.remove(BusinessId(business_id))
        return _view(None)

    return router
