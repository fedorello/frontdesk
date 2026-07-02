"""Owner-facing read of a customer's remembered facts (customer-memory Phase 5)."""

from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

from frontdesk.domain.customer_memory import CustomerFact
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.infrastructure.memory import InMemoryCustomerProfileRepository
from frontdesk.interface.customer_memory_api import build_customer_facts_router

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)


def _client(repo: InMemoryCustomerProfileRepository) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(build_customer_facts_router(repo))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_lists_a_customers_remembered_facts() -> None:
    repo = InMemoryCustomerProfileRepository()
    await repo.upsert_facts(
        BusinessId("biz"), CustomerId("cust"), [CustomerFact("Birth date", "21 Dec 1984", NOW)]
    )

    async with _client(repo) as client:
        response = await client.get("/api/businesses/biz/customers/cust/facts")

    assert response.status_code == 200
    assert response.json() == [{"key": "Birth date", "value": "21 Dec 1984"}]


async def test_is_empty_for_a_customer_with_no_facts() -> None:
    async with _client(InMemoryCustomerProfileRepository()) as client:
        response = await client.get("/api/businesses/biz/customers/nobody/facts")

    assert response.json() == []
