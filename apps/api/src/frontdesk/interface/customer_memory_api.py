"""Owner-facing, read-only view of a customer's remembered facts (customer-memory Phase 5).

Business-scoped and behind the owner guard, so an owner sees what the assistant has remembered about
one of their customers next to the conversation.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from frontdesk.application.ports import CustomerProfileRepository
from frontdesk.domain.ids import BusinessId, CustomerId

Guard = Callable[..., Awaitable[None]] | None


class CustomerFactView(BaseModel):
    key: str
    value: str


def build_customer_facts_router(
    profiles: CustomerProfileRepository, guard: Guard = None
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/customers/{customer_id}/facts")
    async def customer_facts(business_id: str, customer_id: str) -> list[CustomerFactView]:
        profile = await profiles.get(BusinessId(business_id), CustomerId(customer_id))
        return [CustomerFactView(key=fact.key, value=fact.value) for fact in profile.facts]

    return router
