"""The config API creates a bookable business over HTTP (profile, services, hours)."""

import httpx
from fastapi import FastAPI

from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryResourceRepository,
    InMemoryServiceRepository,
)
from frontdesk.interface.config_api import build_config_router


def _client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(
        build_config_router(
            InMemoryBusinessRepository([], {}),
            InMemoryServiceRepository([]),
            InMemoryResourceRepository(),
        )
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_business_profile_roundtrip() -> None:
    async with _client() as client:
        put = await client.put(
            "/api/businesses/ana",
            json={
                "name": "Ana Studio",
                "timezone": "America/Montevideo",
                "description": "A cosy two-chair salon downtown.",
                "knowledge": [{"question": "hours", "answer": "9-5"}],
            },
        )
        assert put.status_code == 200

        got = (await client.get("/api/businesses/ana")).json()
        assert got["name"] == "Ana Studio"
        assert got["description"] == "A cosy two-chair salon downtown."  # round-trips
        assert got["knowledge"][0]["answer"] == "9-5"
        assert (await client.get("/api/businesses/missing")).status_code == 404


async def test_invalid_timezone_is_rejected() -> None:
    async with _client() as client:
        bad = await client.put("/api/businesses/ana", json={"name": "Ana", "timezone": "UTC-3"})
        assert bad.status_code == 422  # not a real IANA key — would crash availability math


async def test_business_address_roundtrips() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana",
            json={"name": "Ana", "timezone": "UTC", "address": "12 Rivera St, Montevideo"},
        )
        got = (await client.get("/api/businesses/ana")).json()
        assert got["address"] == "12 Rivera St, Montevideo"
        assert got["online"] is False


async def test_business_online_roundtrips() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana", json={"name": "Ana", "timezone": "UTC", "online": True}
        )
        got = (await client.get("/api/businesses/ana")).json()
        assert got["online"] is True


async def test_locale_roundtrips_and_dedicated_endpoint() -> None:
    async with _client() as client:
        # Profile carries the locale...
        await client.put(
            "/api/businesses/ana", json={"name": "Ana", "timezone": "UTC", "locale": "ru"}
        )
        assert (await client.get("/api/businesses/ana")).json()["locale"] == "ru"

        # ...and the dedicated endpoint updates just the locale.
        ok = await client.put("/api/businesses/ana/locale", json={"locale": "es"})
        assert ok.json() == {"locale": "es"}
        assert (await client.get("/api/businesses/ana")).json()["locale"] == "es"

        bad = await client.put("/api/businesses/ana/locale", json={"locale": "xx"})
        assert bad.status_code == 422  # unsupported locale rejected


async def test_services_crud() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana/services/svc1",
            json={
                "name": "Haircut",
                "duration_minutes": 60,
                "resource_ids": ["res"],
                "description": "Wash, cut and style.",
                "price_cents": 80000,
                "currency": "uyu",  # lower-case is normalised
                "max_advance_days": 14,
            },
        )
        listed = (await client.get("/api/businesses/ana/services")).json()
        assert len(listed) == 1
        assert listed[0]["id"] == "svc1"
        assert listed[0]["resource_ids"] == ["res"]  # belongs to the "res" group
        assert listed[0]["description"] == "Wash, cut and style."  # round-trips
        assert listed[0]["price_cents"] == 80000
        assert listed[0]["currency"] == "UYU"  # normalised to ISO 4217
        assert listed[0]["max_advance_days"] == 14  # booking horizon round-trips
        assert "working_hours" not in listed[0]  # the schedule lives on the group, not the service

        bad = await client.put(
            "/api/businesses/ana/services/svc2",
            json={"name": "X", "duration_minutes": 30, "max_advance_days": 0},
        )
        assert bad.status_code == 422  # horizon must be positive

        await client.delete("/api/businesses/ana/services/svc1")
        assert (await client.get("/api/businesses/ana/services")).json() == []


async def test_invalid_currency_is_rejected() -> None:
    async with _client() as client:
        bad = await client.put(
            "/api/businesses/ana/services/svc1",
            json={"name": "Cut", "duration_minutes": 30, "currency": "dollars"},
        )
        assert bad.status_code == 422  # not an ISO 4217 code


async def test_groups_crud_and_guarded_delete() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana/resources/res1",
            json={
                "name": "Ana",
                "working_hours": [{"weekday": 0, "opens": "09:00:00", "closes": "17:00:00"}],
            },
        )
        listed = (await client.get("/api/businesses/ana/resources")).json()
        assert listed[0]["id"] == "res1"  # the group id is exposed so services can reference it
        assert listed[0]["name"] == "Ana"
        assert listed[0]["working_hours"][0]["weekday"] == 0  # the group owns the schedule

        # A group with services can't be deleted out from under them.
        await client.put(
            "/api/businesses/ana/services/svc1",
            json={"name": "Cut", "duration_minutes": 30, "resource_ids": ["res1"]},
        )
        blocked = await client.delete("/api/businesses/ana/resources/res1")
        assert blocked.status_code == 409

        # Once its services are moved away, the group deletes.
        await client.delete("/api/businesses/ana/services/svc1")
        ok = await client.delete("/api/businesses/ana/resources/res1")
        assert ok.status_code == 200
        assert (await client.get("/api/businesses/ana/resources")).json() == []


async def test_oversized_name_and_descriptions_are_rejected() -> None:
    async with _client() as client:
        too_long_name = await client.put(
            "/api/businesses/ana", json={"name": "x" * 201, "timezone": "UTC"}
        )
        assert too_long_name.status_code == 422  # name > 200

        too_long_desc = await client.put(
            "/api/businesses/ana",
            json={"name": "Ana", "timezone": "UTC", "description": "x" * 5001},
        )
        assert too_long_desc.status_code == 422  # business description > 5000

        too_long_service = await client.put(
            "/api/businesses/ana/services/svc1",
            json={"name": "S", "duration_minutes": 30, "description": "x" * 5001},
        )
        assert too_long_service.status_code == 422  # service description > 5000


async def test_intake_fields_roundtrip_and_capped_at_five() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana/services/svc1",
            json={
                "name": "Reading",
                "duration_minutes": 60,
                "intake_fields": [
                    {
                        "name": "Birth date",
                        "description": "DOB",
                        "ask": "When were you born?",
                        "normalize": "Format as DD.MM.YYYY",
                    },
                    {"name": "Birth time", "description": "time of birth"},
                ],
            },
        )
        fields = (await client.get("/api/businesses/ana/services")).json()[0]["intake_fields"]
        assert [f["name"] for f in fields] == ["Birth date", "Birth time"]
        assert fields[0]["ask"] == "When were you born?"
        assert fields[0]["normalize"] == "Format as DD.MM.YYYY"  # per-field rule round-trips

        six = await client.put(
            "/api/businesses/ana/services/svc2",
            json={
                "name": "X",
                "duration_minutes": 30,
                "intake_fields": [{"name": f"f{i}"} for i in range(6)],
            },
        )
        assert six.status_code == 422  # at most 5 intake fields
