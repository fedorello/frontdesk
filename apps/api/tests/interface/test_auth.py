"""Accounts: sign up, log in, hashed passwords, signed tokens, and route scoping."""

import httpx
from fastapi import Depends, FastAPI

from frontdesk.core.settings import Settings
from frontdesk.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
)
from frontdesk.infrastructure.security import (
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)
from frontdesk.infrastructure.system import SequentialIdGenerator
from frontdesk.interface.auth import build_auth_router, make_owner_guard

SETTINGS = Settings(secret_key="test-key")


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("hunter2")
    assert hashed != "hunter2"
    assert verify_password("hunter2", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("x", "not-a-valid-hash")


def test_token_roundtrip_and_expiry() -> None:
    token = issue_token("acc-1", "k", issued_at=1000)
    assert verify_token(token, "k", now=1000, max_age=3600) == "acc-1"
    assert verify_token(token, "k", now=1000, max_age=0) == "acc-1"  # 0 = never expires
    assert verify_token(token, "k", now=1000 + 4000, max_age=3600) is None  # expired
    assert verify_token(token, "other-key", now=1000, max_age=3600) is None  # wrong key
    assert verify_token("garbage", "k", now=1000, max_age=3600) is None  # malformed


def _app() -> FastAPI:
    accounts = InMemoryAccountRepository()
    app = FastAPI()
    app.include_router(
        build_auth_router(
            accounts, InMemoryBusinessRepository([], {}), SequentialIdGenerator("id"), SETTINGS
        )
    )
    guard = make_owner_guard(accounts, SETTINGS.secret_key)

    @app.get("/api/businesses/{business_id}/secret", dependencies=[Depends(guard)])
    async def secret(business_id: str) -> dict[str, str]:
        return {"business": business_id}

    return app


async def test_signup_login_and_scoping() -> None:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        signup = await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "test-pw-123", "business_name": "Ana"},
        )
        assert signup.status_code == 200
        token = signup.json()["token"]
        business_id = signup.json()["business_id"]

        dup = await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "test-pw-123", "business_name": "X"},
        )
        assert dup.status_code == 409  # email taken

        login = await client.post(
            "/api/login", json={"email": "a@x.com", "password": "test-pw-123"}
        )
        assert login.status_code == 200
        bad = await client.post("/api/login", json={"email": "a@x.com", "password": "WRONG"})
        assert bad.status_code == 401

        auth = {"authorization": f"Bearer {token}"}
        assert (
            await client.get(f"/api/businesses/{business_id}/secret", headers=auth)
        ).status_code == 200
        assert (await client.get("/api/businesses/other/secret", headers=auth)).status_code == 403
        assert (await client.get(f"/api/businesses/{business_id}/secret")).status_code == 401
