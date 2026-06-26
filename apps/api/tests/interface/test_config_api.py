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
                "timezone": "UTC",
                "knowledge": [{"question": "hours", "answer": "9-5"}],
            },
        )
        assert put.status_code == 200

        got = (await client.get("/api/businesses/ana")).json()
        assert got["name"] == "Ana Studio"
        assert got["knowledge"][0]["answer"] == "9-5"
        assert (await client.get("/api/businesses/missing")).status_code == 404


async def test_services_crud() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana/services/svc1",
            json={"name": "Haircut", "duration_minutes": 60, "resource_ids": ["res"]},
        )
        listed = (await client.get("/api/businesses/ana/services")).json()
        assert len(listed) == 1
        assert listed[0]["id"] == "svc1"
        assert listed[0]["name"] == "Haircut"

        await client.delete("/api/businesses/ana/services/svc1")
        assert (await client.get("/api/businesses/ana/services")).json() == []


async def test_resources_and_hours() -> None:
    async with _client() as client:
        await client.put(
            "/api/businesses/ana/resources/res1",
            json={
                "name": "Ana",
                "working_hours": [{"weekday": 0, "opens": "09:00:00", "closes": "17:00:00"}],
            },
        )
        listed = (await client.get("/api/businesses/ana/resources")).json()
        assert listed[0]["name"] == "Ana"
        assert listed[0]["working_hours"][0]["weekday"] == 0
