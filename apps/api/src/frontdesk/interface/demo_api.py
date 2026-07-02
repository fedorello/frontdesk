"""Public landing-demo endpoint (Phase 4): a Google-signed-in visitor unlocks the demo numbers.

The landing gates the demo behind Google sign-in so we capture the visitor's email as a lead and
protect the telephony/TTS budget from anonymous callers. The browser posts its Google Identity
Services credential; we verify it, record the lead, and return the configured numbers.
"""

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from frontdesk.application.entitlements import RecordDemoLead
from frontdesk.application.ports import GoogleCredentialVerifier, RateLimiter
from frontdesk.domain.entitlements import DemoNumber
from frontdesk.domain.ids import FeatureKey
from frontdesk.interface.client_ip import client_ip


@dataclass(frozen=True)
class DemoAccessConfig:
    feature_key: FeatureKey
    numbers: tuple[DemoNumber, ...]
    rate_limit: int  # requests per window per client IP (0 disables)
    rate_window_seconds: int
    trusted_proxy_hops: int


class DemoAccessRequest(BaseModel):
    credential: str  # a Google Identity Services id_token from the browser


class DemoNumberView(BaseModel):
    language: str
    e164: str
    label: str


class DemoAccessResponse(BaseModel):
    numbers: list[DemoNumberView]


def build_demo_router(
    verifier: GoogleCredentialVerifier,
    recorder: RecordDemoLead,
    config: DemoAccessConfig,
    limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/demo/voice-access")
    async def voice_access(body: DemoAccessRequest, request: Request) -> DemoAccessResponse:
        ip = client_ip(request, config.trusted_proxy_hops)
        if config.rate_limit and not await limiter.hit(
            f"demo:{ip}", config.rate_limit, config.rate_window_seconds
        ):
            raise HTTPException(429, "too many attempts; please wait and try again")
        identity = await verifier.verify(body.credential)
        if identity is None or not identity.email:
            raise HTTPException(401, "google sign-in required")
        await recorder.execute(identity.email, config.feature_key)
        return DemoAccessResponse(numbers=[_number_view(number) for number in config.numbers])

    return router


def _number_view(number: DemoNumber) -> DemoNumberView:
    return DemoNumberView(language=number.language, e164=number.e164, label=number.label)
