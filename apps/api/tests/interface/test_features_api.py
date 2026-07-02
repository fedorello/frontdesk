"""Owner premium-feature endpoints (Phase 2), against in-memory fakes.

The guard is None here so we test the handlers; the owner guard is exercised in test_owner_guard.
"""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.entitlements import FeatureCatalog, RequestFeature
from frontdesk.domain.entitlements import DemoNumber, FeatureRegistry, PremiumFeature
from frontdesk.domain.ids import FeatureKey
from frontdesk.infrastructure.memory import InMemoryEntitlementRepository
from frontdesk.infrastructure.system import FixedClock
from frontdesk.interface.features_api import build_features_router

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")
NUMBERS = (DemoNumber("en", "+16055463259", "English"), DemoNumber("ru", "+19306001900", "Русский"))


def _client() -> httpx.AsyncClient:
    registry = FeatureRegistry(
        [PremiumFeature(VOICE, "Voice receptionist", "Answers calls.", "$1 per call")]
    )
    repo = InMemoryEntitlementRepository()
    app = FastAPI()
    app.include_router(
        build_features_router(
            FeatureCatalog(registry, repo),
            RequestFeature(registry, repo, FixedClock(NOW)),
            None,
            NUMBERS,
        )
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_lists_the_catalog_with_no_status_before_a_request() -> None:
    async with _client() as client:
        response = await client.get("/api/businesses/biz/features")

    assert response.status_code == 200
    assert response.json() == [
        {
            "key": "voice_receptionist",
            "name": "Voice receptionist",
            "description": "Answers calls.",
            "pricing": "$1 per call",
            "status": None,
        }
    ]


async def test_request_then_list_shows_pending() -> None:
    async with _client() as client:
        posted = await client.post("/api/businesses/biz/features/voice_receptionist/request")
        listed = await client.get("/api/businesses/biz/features")

    assert posted.status_code == 200
    assert posted.json()["status"] == "requested"
    assert listed.json()[0]["status"] == "requested"


async def test_lists_the_voice_demo_numbers() -> None:
    async with _client() as client:
        response = await client.get("/api/businesses/biz/voice-demo-numbers")

    assert response.status_code == 200
    assert [(n["language"], n["e164"]) for n in response.json()] == [
        ("en", "+16055463259"),
        ("ru", "+19306001900"),
    ]


async def test_request_unknown_feature_is_404() -> None:
    async with _client() as client:
        response = await client.post("/api/businesses/biz/features/ghost/request")

    assert response.status_code == 404
