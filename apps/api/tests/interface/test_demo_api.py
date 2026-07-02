"""The public landing-demo endpoint (Phase 4): Google-gated, lead-capturing, rate-limited."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.application.entitlements import RecordDemoLead
from frontdesk.application.ports import GoogleIdentity
from frontdesk.domain.entitlements import DemoNumber
from frontdesk.domain.ids import FeatureKey
from frontdesk.infrastructure.memory import (
    FakeGoogleCredentialVerifier,
    InMemoryDemoLeadRepository,
)
from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from frontdesk.interface.demo_api import DemoAccessConfig, build_demo_router

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")
GOOD = "good-credential"
IDENTITY = GoogleIdentity(email="caller@example.com", email_verified=True, name="Caller")
NUMBERS = (DemoNumber("en", "+16055463259", "English"), DemoNumber("ru", "+19306001900", "Русский"))


def _app(leads: InMemoryDemoLeadRepository, *, rate_limit: int = 5) -> FastAPI:
    app = FastAPI()
    app.include_router(
        build_demo_router(
            FakeGoogleCredentialVerifier({GOOD: IDENTITY}),
            RecordDemoLead(leads, SequentialIdGenerator("lead"), FixedClock(NOW)),
            DemoAccessConfig(VOICE, NUMBERS, rate_limit, 3600, 0),
            InMemoryRateLimiter(),
        )
    )
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_valid_credential_returns_numbers_and_records_the_lead() -> None:
    leads = InMemoryDemoLeadRepository()
    async with _client(_app(leads)) as client:
        response = await client.post("/api/demo/voice-access", json={"credential": GOOD})

    assert response.status_code == 200
    assert [n["e164"] for n in response.json()["numbers"]] == ["+16055463259", "+19306001900"]
    assert [(lead.email, lead.feature_key) for lead in leads.leads] == [
        ("caller@example.com", VOICE)
    ]


async def test_an_unverified_credential_is_401_and_records_nothing() -> None:
    leads = InMemoryDemoLeadRepository()
    async with _client(_app(leads)) as client:
        response = await client.post("/api/demo/voice-access", json={"credential": "forged"})

    assert response.status_code == 401
    assert leads.leads == []  # no lead, no numbers leaked


async def test_rate_limit_blocks_after_the_window_budget() -> None:
    async with _client(_app(InMemoryDemoLeadRepository(), rate_limit=1)) as client:
        first = await client.post("/api/demo/voice-access", json={"credential": GOOD})
        second = await client.post("/api/demo/voice-access", json={"credential": GOOD})

    assert first.status_code == 200
    assert second.status_code == 429  # one request per window per IP
