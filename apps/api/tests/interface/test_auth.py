"""Accounts: sign up, log in, hashed passwords, signed tokens, and route scoping."""

import httpx
from fastapi import Depends, FastAPI

from frontdesk.application.ports import Account
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import AccountId, BusinessId
from frontdesk.infrastructure.keys import session_signing_key
from frontdesk.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
    InMemoryResourceRepository,
)
from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter
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
    valid = verify_token(token, "k", now=1000, max_age=3600)
    assert valid is not None
    assert (valid.account_id, valid.issued_at) == ("acc-1", 1000)
    assert verify_token(token, "k", now=1000, max_age=0) is not None  # 0 = never expires
    assert verify_token(token, "k", now=1000 + 4000, max_age=3600) is None  # expired
    assert verify_token(token, "other-key", now=1000, max_age=3600) is None  # wrong key
    assert verify_token("garbage", "k", now=1000, max_age=3600) is None  # malformed


def _app() -> FastAPI:
    accounts = InMemoryAccountRepository()
    app = FastAPI()
    app.include_router(
        build_auth_router(
            accounts,
            InMemoryBusinessRepository([], {}),
            InMemoryResourceRepository(),
            SequentialIdGenerator("id"),
            SETTINGS,
            InMemoryRateLimiter(),
        )
    )
    guard = make_owner_guard(accounts, session_signing_key(SETTINGS.secret_key))

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
        assert "tovayo.session" in signup.cookies  # token delivered as an HttpOnly cookie
        assert "token" not in signup.json()  # never in the response body
        business_id = signup.json()["business_id"]

        dup = await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "test-pw-123", "business_name": "X"},
        )
        assert dup.status_code == 409  # email taken

        bad = await client.post("/api/login", json={"email": "a@x.com", "password": "WRONG"})
        assert bad.status_code == 401
        login = await client.post(
            "/api/login", json={"email": "a@x.com", "password": "test-pw-123"}
        )
        assert login.status_code == 200

        # The session cookie (carried by the client jar) authenticates — no Authorization header.
        assert (await client.get(f"/api/businesses/{business_id}/secret")).status_code == 200
        assert (await client.get("/api/businesses/other/secret")).status_code == 403  # not mine

        await client.post("/api/logout")  # clears the cookie
        assert (await client.get(f"/api/businesses/{business_id}/secret")).status_code == 401


async def test_email_is_validated_and_normalized() -> None:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post(
            "/api/signup",
            json={"email": "not-an-email", "password": "test-pw-123", "business_name": "X"},
        )
        assert bad.status_code == 422  # EmailStr rejects a malformed address

        up = await client.post(
            "/api/signup",
            json={"email": "Owner@Example.COM", "password": "test-pw-123", "business_name": "X"},
        )
        assert up.status_code == 200

        dup = await client.post(
            "/api/signup",
            json={"email": "owner@example.com", "password": "test-pw-123", "business_name": "Y"},
        )
        assert dup.status_code == 409  # normalized to the same address → already registered

        login = await client.post(
            "/api/login", json={"email": "OWNER@EXAMPLE.COM", "password": "test-pw-123"}
        )
        assert login.status_code == 200  # login is case-insensitive too


async def test_login_is_rate_limited() -> None:
    accounts = InMemoryAccountRepository()
    settings = Settings(secret_key="k", login_rate_limit=2, login_rate_window_seconds=300)
    app = FastAPI()
    app.include_router(
        build_auth_router(
            accounts,
            InMemoryBusinessRepository([], {}),
            InMemoryResourceRepository(),
            SequentialIdGenerator("id"),
            settings,
            InMemoryRateLimiter(),
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        creds = {"email": "x@x.com", "password": "nope-12345"}
        for _ in range(2):  # within the limit: bad credentials → 401
            assert (await client.post("/api/login", json=creds)).status_code == 401
        # the third attempt from the same IP trips the limiter
        assert (await client.post("/api/login", json=creds)).status_code == 429


async def test_signup_creates_a_default_group() -> None:
    accounts = InMemoryAccountRepository()
    resources = InMemoryResourceRepository()
    app = FastAPI()
    app.include_router(
        build_auth_router(
            accounts,
            InMemoryBusinessRepository([], {}),
            resources,
            SequentialIdGenerator("id"),
            SETTINGS,
            InMemoryRateLimiter(),
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        signup = await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "test-pw-123", "business_name": "Ana"},
        )
        business_id = signup.json()["business_id"]

    # Every new business starts with exactly one group + a default schedule, so services
    # always have a valid calendar (no phantom group).
    groups = await resources.for_business(BusinessId(business_id))
    assert len(groups) == 1
    assert groups[0].working_hours  # a starter weekly schedule


def _auth_app(accounts: InMemoryAccountRepository) -> FastAPI:
    app = FastAPI()
    app.include_router(
        build_auth_router(
            accounts,
            InMemoryBusinessRepository([], {}),
            InMemoryResourceRepository(),
            SequentialIdGenerator("id"),
            SETTINGS,
            InMemoryRateLimiter(),
        )
    )
    return app


async def test_guard_rejects_a_token_issued_before_the_revocation_cutoff() -> None:
    accounts = InMemoryAccountRepository()
    key = session_signing_key(SETTINGS.secret_key)
    await accounts.upsert(
        Account(AccountId("acc"), "a@x.com", "h", BusinessId("biz"), sessions_valid_after=5000)
    )
    app = FastAPI()
    guard = make_owner_guard(accounts, key)

    @app.get("/api/businesses/{business_id}/secret", dependencies=[Depends(guard)])
    async def secret(business_id: str) -> dict[str, str]:
        return {"ok": business_id}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        stale = {"Authorization": f"Bearer {issue_token('acc', key, issued_at=1000)}"}  # < cutoff
        fresh = {"Authorization": f"Bearer {issue_token('acc', key, issued_at=6000)}"}  # >= cutoff
        assert (await client.get("/api/businesses/biz/secret", headers=stale)).status_code == 401
        assert (await client.get("/api/businesses/biz/secret", headers=fresh)).status_code == 200


async def test_logout_revokes_existing_sessions() -> None:
    accounts = InMemoryAccountRepository()
    transport = httpx.ASGITransport(app=_auth_app(accounts))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "test-pw-123", "business_name": "Ana"},
        )
        before = await accounts.by_email("a@x.com")
        assert before is not None
        assert before.sessions_valid_after == 0  # fresh account

        await client.post("/api/logout")

        after = await accounts.by_email("a@x.com")
        assert after is not None
        assert after.sessions_valid_after > 0  # the cutoff is bumped → prior tokens are rejected


async def test_password_change_rehashes_and_revokes_other_sessions() -> None:
    accounts = InMemoryAccountRepository()
    transport = httpx.ASGITransport(app=_auth_app(accounts))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/signup",
            json={"email": "a@x.com", "password": "old-pw-123", "business_name": "Ana"},
        )

        wrong = await client.post(
            "/api/account/password",
            json={"current_password": "WRONG", "new_password": "new-pw-456"},
        )
        assert wrong.status_code == 403  # must prove the current password

        ok = await client.post(
            "/api/account/password",
            json={"current_password": "old-pw-123", "new_password": "new-pw-456"},
        )
        assert ok.status_code == 200

        account = await accounts.by_email("a@x.com")
        assert account is not None
        assert verify_password("new-pw-456", account.password_hash)  # rehashed
        assert account.sessions_valid_after > 0  # other sessions revoked
        # This session survives (a fresh cookie was set) and the new password works.
        login = await client.post("/api/login", json={"email": "a@x.com", "password": "new-pw-456"})
        assert login.status_code == 200


async def test_password_change_requires_authentication() -> None:
    accounts = InMemoryAccountRepository()
    transport = httpx.ASGITransport(app=_auth_app(accounts))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/account/password",
            json={"current_password": "x", "new_password": "new-pw-456"},
        )
        assert response.status_code == 401  # no session


async def test_logout_without_a_session_is_a_safe_noop() -> None:
    accounts = InMemoryAccountRepository()
    transport = httpx.ASGITransport(app=_auth_app(accounts))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/logout")
        assert response.status_code == 200  # nothing to revoke, still idempotent ok
