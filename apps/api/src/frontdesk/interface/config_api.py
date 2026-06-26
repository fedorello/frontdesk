"""Business configuration write-API (M2): profile, services, resources/hours.

Lets an owner configure a bookable business entirely over HTTP — no SQL. The LLM
provider lives in its own router (``business_config.py``).
"""

from collections.abc import Awaitable, Callable
from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.ports import (
    BusinessRepository,
    ResourceRepository,
    ServiceRepository,
)
from frontdesk.domain.ids import BusinessId, ResourceId, ServiceId
from frontdesk.domain.models import Business, KnowledgeItem, Resource, Service, WorkingHours
from frontdesk.domain.money import Money

Guard = Callable[..., Awaitable[None]] | None


class KnowledgeItemIO(BaseModel):
    question: str
    answer: str


class BusinessProfile(BaseModel):
    name: str
    timezone: str
    lead_time_minutes: int = 0
    buffer_minutes: int = 0
    knowledge: list[KnowledgeItemIO] = []


class ServiceIO(BaseModel):
    name: str
    duration_minutes: int
    price_cents: int | None = None
    currency: str | None = None
    resource_ids: list[str] = []


class ServiceView(ServiceIO):
    id: str


class WorkingHoursIO(BaseModel):
    weekday: int
    opens: str  # "HH:MM:SS"
    closes: str


class ResourceIO(BaseModel):
    name: str
    working_hours: list[WorkingHoursIO] = []


def _service_view(service: Service) -> ServiceView:
    return ServiceView(
        id=str(service.id),
        name=service.name,
        duration_minutes=service.duration_minutes,
        price_cents=service.price.amount_cents if service.price else None,
        currency=service.price.currency if service.price else None,
        resource_ids=[str(r) for r in service.resource_ids],
    )


def build_config_router(
    businesses: BusinessRepository,
    services: ServiceRepository,
    resources: ResourceRepository,
    guard: Guard = None,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.put("/api/businesses/{business_id}")
    async def put_business(business_id: str, body: BusinessProfile) -> BusinessProfile:
        await businesses.upsert(
            Business(
                BusinessId(business_id),
                body.name,
                body.timezone,
                lead_time_minutes=body.lead_time_minutes,
                buffer_minutes=body.buffer_minutes,
                knowledge=tuple(KnowledgeItem(k.question, k.answer) for k in body.knowledge),
            )
        )
        return body

    @router.get("/api/businesses/{business_id}")
    async def get_business(business_id: str) -> BusinessProfile:
        business = await businesses.find(BusinessId(business_id))
        if business is None:
            raise HTTPException(404, "business not found")
        return BusinessProfile(
            name=business.name,
            timezone=business.timezone,
            lead_time_minutes=business.lead_time_minutes,
            buffer_minutes=business.buffer_minutes,
            knowledge=[
                KnowledgeItemIO(question=k.question, answer=k.answer) for k in business.knowledge
            ],
        )

    @router.get("/api/businesses/{business_id}/services")
    async def list_services(business_id: str) -> list[ServiceView]:
        return [_service_view(s) for s in await services.for_business(BusinessId(business_id))]

    @router.put("/api/businesses/{business_id}/services/{service_id}")
    async def put_service(business_id: str, service_id: str, body: ServiceIO) -> ServiceView:
        price = (
            Money(body.price_cents, body.currency)
            if body.price_cents is not None and body.currency
            else None
        )
        service = Service(
            ServiceId(service_id),
            BusinessId(business_id),
            body.name,
            body.duration_minutes,
            price,
            tuple(ResourceId(r) for r in body.resource_ids),
        )
        await services.upsert(service)
        return _service_view(service)

    @router.delete("/api/businesses/{business_id}/services/{service_id}")
    async def delete_service(business_id: str, service_id: str) -> dict[str, str]:
        await services.remove(ServiceId(service_id))
        return {"status": "deleted"}

    @router.get("/api/businesses/{business_id}/resources")
    async def list_resources(business_id: str) -> list[ResourceIO]:
        return [
            ResourceIO(
                name=r.name,
                working_hours=[
                    WorkingHoursIO(
                        weekday=h.weekday, opens=h.opens.isoformat(), closes=h.closes.isoformat()
                    )
                    for h in r.working_hours
                ],
            )
            for r in await resources.for_business(BusinessId(business_id))
        ]

    @router.put("/api/businesses/{business_id}/resources/{resource_id}")
    async def put_resource(business_id: str, resource_id: str, body: ResourceIO) -> ResourceIO:
        await resources.upsert(
            Resource(
                ResourceId(resource_id),
                BusinessId(business_id),
                body.name,
                tuple(
                    WorkingHours(
                        h.weekday, time.fromisoformat(h.opens), time.fromisoformat(h.closes)
                    )
                    for h in body.working_hours
                ),
            )
        )
        return body

    return router
