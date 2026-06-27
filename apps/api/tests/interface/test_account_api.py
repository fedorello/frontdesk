"""The delete-account endpoint erases the business and returns 204."""

import httpx
from fastapi import FastAPI

from frontdesk.domain.ids import BusinessId
from frontdesk.interface.account_api import build_account_router


class FakeEraser:
    def __init__(self) -> None:
        self.erased: list[BusinessId] = []

    async def erase(self, business_id: BusinessId) -> None:
        self.erased.append(business_id)


async def test_delete_account_erases_the_business() -> None:
    eraser = FakeEraser()
    app = FastAPI()
    app.include_router(build_account_router(eraser))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/api/businesses/biz")

    assert response.status_code == 204
    assert eraser.erased == [BusinessId("biz")]
