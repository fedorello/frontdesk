"""Sign in with Google: start redirect, callback creates/reuses the owner's account."""

from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import FastAPI

from frontdesk.application.ports import GoogleIdentity, GoogleOAuthClient
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
)
from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter
from frontdesk.infrastructure.system import SequentialIdGenerator
from frontdesk.interface.google_auth import build_google_auth_router

SETTINGS = Settings(
    secret_key="test-key",
    google_client_id="client-123",
    google_redirect_uri="https://api.test/api/auth/google/callback",
    dashboard_url="https://app.test",
)


class FakeGoogleOAuthClient:
    def __init__(self, identity: GoogleIdentity) -> None:
        self.identity = identity
        self.codes: list[str] = []

    async def exchange_code(self, code: str) -> GoogleIdentity:
        self.codes.append(code)
        return self.identity


def _app(
    oauth: GoogleOAuthClient,
    accounts: InMemoryAccountRepository | None = None,
    settings: Settings = SETTINGS,
) -> tuple[FastAPI, InMemoryAccountRepository]:
    accounts = accounts if accounts is not None else InMemoryAccountRepository()
    app = FastAPI()
    app.include_router(
        build_google_auth_router(
            oauth,
            accounts,
            InMemoryBusinessRepository([], {}),
            SequentialIdGenerator("id"),
            settings,
            InMemoryRateLimiter(),
        )
    )
    return app, accounts


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", follow_redirects=False
    )


def _query(location: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(location).query)


async def test_start_redirects_to_google() -> None:
    app, _ = _app(FakeGoogleOAuthClient(GoogleIdentity("a@x.com", email_verified=True, name="Ann")))
    async with _client(app) as client:
        resp = await client.get("/api/auth/google/start")
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    query = _query(location)
    assert query["client_id"] == ["client-123"]
    assert query["redirect_uri"] == ["https://api.test/api/auth/google/callback"]
    assert query["state"][0]  # CSRF state present


async def test_callback_creates_account_then_reuses_it() -> None:
    oauth = FakeGoogleOAuthClient(
        GoogleIdentity("new@x.com", email_verified=True, name="New Owner")
    )
    app, accounts = _app(oauth)
    async with _client(app) as client:
        start = await client.get("/api/auth/google/start")
        state = _query(start.headers["location"])["state"][0]

        first = await client.get(
            "/api/auth/google/callback", params={"code": "abc", "state": state}
        )
        assert first.status_code == 302
        dest = first.headers["location"]
        assert dest.startswith("https://app.test/auth/callback?")
        first_q = _query(dest)
        business_id = first_q["business_id"][0]
        assert business_id
        assert "token" not in first_q  # the token is in the cookie, never the URL
        assert "tovayo.session" in first.cookies  # session delivered as an HttpOnly cookie

        account = await accounts.by_email("new@x.com")
        assert account is not None
        assert str(account.business_id) == business_id

        # a second sign-in reuses the same account + business
        start2 = await client.get("/api/auth/google/start")
        state2 = _query(start2.headers["location"])["state"][0]
        second = await client.get(
            "/api/auth/google/callback", params={"code": "def", "state": state2}
        )
        assert _query(second.headers["location"])["business_id"][0] == business_id


async def test_callback_rejects_forged_state() -> None:
    app, _ = _app(FakeGoogleOAuthClient(GoogleIdentity("a@x.com", email_verified=True, name="A")))
    async with _client(app) as client:
        resp = await client.get(
            "/api/auth/google/callback", params={"code": "x", "state": "forged"}
        )
    assert resp.status_code == 302
    assert "/login?error=google" in resp.headers["location"]


async def test_callback_rejects_unverified_email() -> None:
    oauth = FakeGoogleOAuthClient(GoogleIdentity("a@x.com", email_verified=False, name="A"))
    app, accounts = _app(oauth)
    async with _client(app) as client:
        start = await client.get("/api/auth/google/start")
        state = _query(start.headers["location"])["state"][0]
        resp = await client.get("/api/auth/google/callback", params={"code": "x", "state": state})
    assert "/login?error=google" in resp.headers["location"]
    assert await accounts.by_email("a@x.com") is None  # no account created


async def test_disabled_when_unconfigured() -> None:
    oauth = FakeGoogleOAuthClient(GoogleIdentity("a@x.com", email_verified=True, name="A"))
    app, _ = _app(oauth, settings=Settings(secret_key="k"))  # no google_client_id
    async with _client(app) as client:
        resp = await client.get("/api/auth/google/start")
    assert resp.status_code == 302
    assert "/login?error=google" in resp.headers["location"]
