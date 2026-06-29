"""The admin guard and /api/me (ADR-0012): an admin passes, an owner is forbidden."""

import time

import httpx
from fastapi import Depends, FastAPI

from frontdesk.application.ports import Account
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import UserRole
from frontdesk.domain.ids import AccountId, BusinessId
from frontdesk.infrastructure.keys import session_signing_key
from frontdesk.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
    InMemoryResourceRepository,
)
from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter
from frontdesk.infrastructure.security import issue_token
from frontdesk.infrastructure.system import SequentialIdGenerator
from frontdesk.interface.auth import build_auth_router, build_me_router, make_admin_guard
from frontdesk.interface.cookies import SESSION_COOKIE

SETTINGS = Settings(secret_key="test-key")
_KEY = session_signing_key(SETTINGS.secret_key)


async def _accounts() -> InMemoryAccountRepository:
    accounts = InMemoryAccountRepository()
    await accounts.upsert(Account(AccountId("adm"), "ops@x.com", "h", None, role=UserRole.ADMIN))
    await accounts.upsert(Account(AccountId("own"), "o@x.com", "h", BusinessId("biz")))
    return accounts


def _app(accounts: InMemoryAccountRepository) -> FastAPI:
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
    app.include_router(build_me_router(accounts, SETTINGS))
    guard = make_admin_guard(accounts, _KEY, SETTINGS.token_max_age_seconds)

    @app.get("/api/admin/ping", dependencies=[Depends(guard)])
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    return app


def _token(account_id: str, *, issued_at: int | None = None) -> str:
    return issue_token(account_id, _KEY, issued_at if issued_at is not None else int(time.time()))


async def _get(
    accounts: InMemoryAccountRepository, path: str, token: str | None = None
) -> httpx.Response:
    # Cookies are set on the client instance (not per-request) to match httpx's supported usage.
    transport = httpx.ASGITransport(app=_app(accounts))
    cookies = {SESSION_COOKIE: token} if token is not None else None
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", cookies=cookies
    ) as client:
        return await client.get(path)


async def test_admin_token_passes_the_guard() -> None:
    response = await _get(await _accounts(), "/api/admin/ping", _token("adm"))

    assert response.status_code == 200


async def test_owner_token_is_forbidden() -> None:
    response = await _get(await _accounts(), "/api/admin/ping", _token("own"))

    assert response.status_code == 403


async def test_missing_token_is_unauthenticated() -> None:
    response = await _get(await _accounts(), "/api/admin/ping")

    assert response.status_code == 401


async def test_expired_token_is_unauthenticated() -> None:
    stale = _token("adm", issued_at=int(time.time()) - SETTINGS.token_max_age_seconds - 10)
    response = await _get(await _accounts(), "/api/admin/ping", stale)

    assert response.status_code == 401


async def test_me_returns_admin_identity() -> None:
    response = await _get(await _accounts(), "/api/me", _token("adm"))

    assert response.status_code == 200
    assert response.json() == {"email": "ops@x.com", "business_id": None, "role": "admin"}


async def test_me_returns_owner_identity_with_business() -> None:
    response = await _get(await _accounts(), "/api/me", _token("own"))

    assert response.json() == {"email": "o@x.com", "business_id": "biz", "role": "owner"}


async def test_me_without_token_is_unauthenticated() -> None:
    response = await _get(await _accounts(), "/api/me")

    assert response.status_code == 401
