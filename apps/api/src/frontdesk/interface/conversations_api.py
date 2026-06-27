"""Owner takeover endpoints: reply to a customer by hand, and hand the chat back to the AI."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from frontdesk.application.owner_actions import OwnerSendMessage, SetConversationHandoff
from frontdesk.domain.errors import TenantMismatch
from frontdesk.domain.ids import BusinessId, CustomerId

Guard = Callable[..., Awaitable[None]] | None

_NOT_FOUND = 404
_MAX_MESSAGE = 4000


class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=_MAX_MESSAGE)


class HandoffInput(BaseModel):
    handled: bool


class OkResult(BaseModel):
    handled: bool


def build_conversations_router(
    send: OwnerSendMessage, handoff: SetConversationHandoff, guard: Guard = None
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])
    base = "/api/businesses/{business_id}/conversations/{customer_id}"

    @router.post(f"{base}/messages")
    async def send_message(business_id: str, customer_id: str, body: MessageInput) -> OkResult:
        try:
            await send(BusinessId(business_id), CustomerId(customer_id), body.text)
        except (KeyError, TenantMismatch) as error:
            raise HTTPException(_NOT_FOUND, "customer not found") from error
        return OkResult(handled=True)  # sending takes the conversation over

    @router.post(f"{base}/handoff")
    async def set_handoff(business_id: str, customer_id: str, body: HandoffInput) -> OkResult:
        try:
            await handoff(BusinessId(business_id), CustomerId(customer_id), body.handled)
        except (KeyError, TenantMismatch) as error:
            raise HTTPException(_NOT_FOUND, "customer not found") from error
        return OkResult(handled=body.handled)

    return router
