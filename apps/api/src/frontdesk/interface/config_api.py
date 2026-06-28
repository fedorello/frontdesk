"""Business configuration write-API (M2): profile, services, resources/hours.

Lets an owner configure a bookable business entirely over HTTP — no SQL. The LLM
provider lives in its own router (``business_config.py``).
"""

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from frontdesk.application.ports import (
    BusinessRepository,
    ResourceRepository,
    ServiceRepository,
)
from frontdesk.domain.ids import BusinessId, ResourceId, ServiceId
from frontdesk.domain.models import (
    MAX_INTAKE_FIELDS,
    Business,
    IntakeField,
    KnowledgeItem,
    Resource,
    Service,
    WorkingHours,
)
from frontdesk.domain.money import Money

Guard = Callable[..., Awaitable[None]] | None
_ISO_4217_LENGTH = 3  # currency codes are three letters, e.g. USD, EUR, UYU
_SUPPORTED_LOCALES = frozenset({"en", "es", "ru", "zh"})
MAX_NAME = 200  # business name
MAX_DESCRIPTION = 5000  # business + service descriptions


class KnowledgeItemIO(BaseModel):
    question: str
    answer: str


class WorkingHoursIO(BaseModel):
    weekday: int  # Monday = 0
    opens: str  # "HH:MM:SS"
    closes: str


class IntakeFieldIO(BaseModel):
    name: str = Field(max_length=MAX_NAME)
    description: str = Field(default="", max_length=MAX_DESCRIPTION)
    ask: str = Field(default="", max_length=MAX_DESCRIPTION)


class BusinessProfile(BaseModel):
    name: str = Field(max_length=MAX_NAME)
    timezone: str
    lead_time_minutes: int = 0
    buffer_minutes: int = 0
    knowledge: list[KnowledgeItemIO] = []
    description: str = Field(default="", max_length=MAX_DESCRIPTION)
    address: str = ""
    online: bool = False
    locale: str = "en"
    owner_name: str = Field(default="", max_length=MAX_NAME)

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        # Reject anything ZoneInfo can't load (e.g. "UTC-3"); availability math needs a
        # real IANA key, otherwise booking crashes at runtime.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone: {value}") from exc
        return value

    @field_validator("locale")
    @classmethod
    def _valid_locale(cls, value: str) -> str:
        if value not in _SUPPORTED_LOCALES:
            raise ValueError(f"unsupported locale: {value}")
        return value


class LocaleInput(BaseModel):
    locale: str

    @field_validator("locale")
    @classmethod
    def _valid_locale(cls, value: str) -> str:
        if value not in _SUPPORTED_LOCALES:
            raise ValueError(f"unsupported locale: {value}")
        return value


class ServiceIO(BaseModel):
    name: str
    duration_minutes: int
    price_cents: int | None = None
    currency: str | None = None
    resource_ids: list[str] = []  # the single group this service belongs to
    description: str = Field(default="", max_length=MAX_DESCRIPTION)
    max_advance_days: int = 30
    intake_fields: list[IntakeFieldIO] = Field(default=[], max_length=MAX_INTAKE_FIELDS)
    requires_confirmation: bool = False

    @field_validator("max_advance_days")
    @classmethod
    def _positive_horizon(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_advance_days must be positive")
        return value

    @field_validator("currency")
    @classmethod
    def _valid_currency(cls, value: str | None) -> str | None:
        # ISO 4217 alpha code, or absent. The UI offers a fixed list; this guards the API.
        if not value:
            return None
        code = value.strip().upper()
        if len(code) != _ISO_4217_LENGTH or not code.isalpha():
            raise ValueError(f"invalid currency: {value}")
        return code


class ServiceView(ServiceIO):
    id: str


class ResourceIO(BaseModel):
    """A service group: a name + the weekly schedule shared by its services."""

    name: str
    working_hours: list[WorkingHoursIO] = []


class ResourceView(ResourceIO):
    id: str


def _to_hours(items: list[WorkingHoursIO]) -> tuple[WorkingHours, ...]:
    return tuple(
        WorkingHours(h.weekday, time.fromisoformat(h.opens), time.fromisoformat(h.closes))
        for h in items
    )


def _hours_io(hours: tuple[WorkingHours, ...]) -> list[WorkingHoursIO]:
    return [
        WorkingHoursIO(weekday=h.weekday, opens=h.opens.isoformat(), closes=h.closes.isoformat())
        for h in hours
    ]


def _service_view(service: Service) -> ServiceView:
    return ServiceView(
        id=str(service.id),
        name=service.name,
        duration_minutes=service.duration_minutes,
        price_cents=service.price.amount_cents if service.price else None,
        currency=service.price.currency if service.price else None,
        resource_ids=[str(r) for r in service.resource_ids],
        description=service.description,
        max_advance_days=service.max_advance_days,
        intake_fields=[
            IntakeFieldIO(name=f.name, description=f.description, ask=f.ask)
            for f in service.intake_fields
        ],
        requires_confirmation=service.requires_confirmation,
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
                description=body.description,
                address=body.address,
                online=body.online,
                locale=body.locale,
                owner_name=body.owner_name,
            )
        )
        return body

    @router.put("/api/businesses/{business_id}/locale")
    async def put_locale(business_id: str, body: LocaleInput) -> dict[str, str]:
        business = await businesses.find(BusinessId(business_id))
        if business is None:
            raise HTTPException(404, "business not found")
        await businesses.upsert(replace(business, locale=body.locale))
        return {"locale": body.locale}

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
            description=business.description,
            address=business.address,
            online=business.online,
            locale=business.locale,
            owner_name=business.owner_name,
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
            description=body.description,
            max_advance_days=body.max_advance_days,
            intake_fields=tuple(
                IntakeField(f.name, f.description, f.ask) for f in body.intake_fields
            ),
            requires_confirmation=body.requires_confirmation,
        )
        await services.upsert(service)
        return _service_view(service)

    @router.delete("/api/businesses/{business_id}/services/{service_id}")
    async def delete_service(business_id: str, service_id: str) -> dict[str, str]:
        await services.remove(ServiceId(service_id), BusinessId(business_id))
        return {"status": "deleted"}

    @router.get("/api/businesses/{business_id}/resources")
    async def list_resources(business_id: str) -> list[ResourceView]:
        return [
            ResourceView(id=str(r.id), name=r.name, working_hours=_hours_io(r.working_hours))
            for r in await resources.for_business(BusinessId(business_id))
        ]

    @router.put("/api/businesses/{business_id}/resources/{resource_id}")
    async def put_resource(business_id: str, resource_id: str, body: ResourceIO) -> ResourceIO:
        await resources.upsert(
            Resource(
                ResourceId(resource_id),
                BusinessId(business_id),
                body.name,
                _to_hours(body.working_hours),
            )
        )
        return body

    @router.delete("/api/businesses/{business_id}/resources/{resource_id}")
    async def delete_resource(business_id: str, resource_id: str) -> dict[str, str]:
        # A group with services can't be deleted out from under them (and its services'
        # appointments) — the owner reassigns those services to another group first.
        members = [
            s
            for s in await services.for_business(BusinessId(business_id))
            if ResourceId(resource_id) in s.resource_ids
        ]
        if members:
            raise HTTPException(409, "move this group's services to another group first")
        await resources.remove(ResourceId(resource_id), BusinessId(business_id))
        return {"status": "deleted"}

    return router
