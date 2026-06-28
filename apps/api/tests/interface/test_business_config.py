"""The LLM config API stores the key but never returns it (only a hint)."""

import httpx
from fastapi import FastAPI

from frontdesk.domain.ids import BusinessId
from frontdesk.infrastructure.memory import InMemoryLlmConfigRepository
from frontdesk.interface.business_config import build_llm_config_router


def _client(repo: InMemoryLlmConfigRepository, *, allow_own_llm: bool = True) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(build_llm_config_router(repo, allow_own_llm=allow_own_llm))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_set_own_provider_hides_the_key() -> None:
    repo = InMemoryLlmConfigRepository()
    async with _client(repo) as client:
        put = await client.put(
            "/api/businesses/biz/llm",
            json={
                "mode": "own",
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-secret-1234",
            },
        )
        body = put.json()
        assert put.status_code == 200
        assert body["provider"] == "openai"
        assert body["api_key_hint"] == "1234"
        assert "api_key" not in body  # the key is never returned

        got = (await client.get("/api/businesses/biz/llm")).json()
        assert got["mode"] == "own"
        assert "api_key" not in got

    # ...but it IS stored (encrypted in prod), available to the assistant.
    stored = await repo.get(BusinessId("biz"))
    assert stored is not None
    assert stored.api_key == "sk-secret-1234"


async def test_default_mode_needs_no_key() -> None:
    repo = InMemoryLlmConfigRepository()
    async with _client(repo) as client:
        assert (await client.get("/api/businesses/new/llm")).json()["mode"] == "default"
        put = await client.put("/api/businesses/biz/llm", json={"mode": "default"})
        assert put.status_code == 200
        assert put.json() == {
            "mode": "default",
            "provider": None,
            "model": None,
            "base_url": None,
            "api_key_hint": None,
        }


async def test_own_mode_validates_inputs() -> None:
    repo = InMemoryLlmConfigRepository()
    async with _client(repo) as client:
        bad_provider = await client.put(
            "/api/businesses/biz/llm",
            json={"mode": "own", "provider": "x", "model": "m", "api_key": "k"},
        )
        no_key = await client.put(
            "/api/businesses/biz/llm", json={"mode": "own", "provider": "openai", "model": "m"}
        )
        bad_mode = await client.put("/api/businesses/biz/llm", json={"mode": "weird"})

    assert (bad_provider.status_code, no_key.status_code, bad_mode.status_code) == (422, 422, 422)


async def test_own_mode_rejected_when_the_feature_is_off() -> None:
    repo = InMemoryLlmConfigRepository()
    async with _client(repo, allow_own_llm=False) as client:
        # The "bring your own provider" feature isn't launched: own mode is forbidden...
        own = await client.put(
            "/api/businesses/biz/llm",
            json={"mode": "own", "provider": "openai", "model": "gpt-4o", "api_key": "sk-x"},
        )
        assert own.status_code == 403
        assert await repo.get(BusinessId("biz")) is None  # nothing stored

        # ...but the managed default still works.
        default = await client.put("/api/businesses/biz/llm", json={"mode": "default"})
        assert default.status_code == 200
