"""The usage endpoint reports today's managed-default count and the limit."""

import httpx
from fastapi import FastAPI

from frontdesk.core.settings import Settings
from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.memory import InMemoryUsageStore
from frontdesk.infrastructure.system import FixedClock
from frontdesk.interface.metrics_api import build_metrics_router
from tests.port_contracts import NOW


async def test_usage_today() -> None:
    usage = InMemoryUsageStore()
    day = NOW.date().isoformat()
    await usage.increment_and_count(BusinessId("biz"), day)
    await usage.increment_and_count(BusinessId("biz"), day)

    app = FastAPI()
    app.include_router(
        build_metrics_router(usage, Settings(managed_default_daily_limit=50), FixedClock(NOW))
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        body = (await client.get("/api/businesses/biz/usage")).json()
        assert body == {"day": day, "used": 2, "limit": 50}

        other = (await client.get("/api/businesses/other/usage")).json()
        assert other["used"] == 0  # a business with no usage today
