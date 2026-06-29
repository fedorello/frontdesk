"""Owner accounts: sign up, log in, log out, and a guard that scopes routes to the owner.

Tokens are HMAC-signed (``security.py``) and delivered in an HttpOnly cookie (``cookies.py``),
never in the response body or a URL. One account owns one business; the guard rejects any
request whose token doesn't own the business in the path. Security events are logged (no PII).
"""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from frontdesk.application.ports import (
    Account,
    AccountRepository,
    BusinessRepository,
    IdGenerator,
    RateLimiter,
    ResourceRepository,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import UserRole
from frontdesk.domain.ids import AccountId, BusinessId, ResourceId
from frontdesk.domain.models import Business, default_group
from frontdesk.infrastructure.keys import session_signing_key
from frontdesk.infrastructure.security import (
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)
from frontdesk.interface.client_ip import client_ip
from frontdesk.interface.cookies import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_session_cookie,
)

_MIN_PASSWORD_LENGTH = 8
_logger = logging.getLogger("frontdesk.auth")


class SignupInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)
    business_name: str
    timezone: str = "UTC"


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=_MIN_PASSWORD_LENGTH)


def _normalize_email(email: str) -> str:
    # Case-insensitive uniqueness + lookup: store and match the lowercased address.
    return email.strip().lower()


class AuthView(BaseModel):
    """What the client gets back — the business to scope its calls to, and the owner's email.

    The auth token is NOT here: it lives only in the HttpOnly session cookie.
    """

    business_id: str
    email: str
    role: str


class MeView(BaseModel):
    """The signed-in account, read from the session cookie. An admin has no business."""

    email: str
    business_id: str | None
    role: str


def build_auth_router(
    accounts: AccountRepository,
    businesses: BusinessRepository,
    resources: ResourceRepository,
    ids: IdGenerator,
    settings: Settings,
    limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()
    signing_key = session_signing_key(settings.secret_key)  # purpose-separated from encryption

    async def _throttle(request: Request, action: str, limit: int, window: int) -> None:
        ip = client_ip(request, settings.trusted_proxy_hops)
        if limit and not await limiter.hit(f"{action}:{ip}", limit, window):
            _logger.warning("rate limited: %s ip=%s", action, ip)
            raise HTTPException(429, "too many attempts; please wait and try again")

    @router.post("/api/signup")
    async def signup(body: SignupInput, request: Request, response: Response) -> AuthView:
        await _throttle(
            request, "signup", settings.signup_rate_limit, settings.signup_rate_window_seconds
        )
        email = _normalize_email(body.email)
        if await accounts.by_email(email) is not None:
            raise HTTPException(409, "email already registered")
        business_id = BusinessId(ids.new())
        await businesses.upsert(Business(business_id, body.business_name, body.timezone))
        # Every business starts with one group, so services always have a valid calendar.
        await resources.upsert(default_group(business_id, ResourceId(ids.new())))
        account = Account(AccountId(ids.new()), email, hash_password(body.password), business_id)
        await accounts.upsert(account)
        set_session_cookie(
            response, issue_token(account.id, signing_key, int(time.time())), settings
        )
        _logger.info("signup account=%s business=%s", account.id, business_id)
        return AuthView(business_id=business_id, email=account.email, role=account.role.value)

    @router.post("/api/login")
    async def login(body: LoginInput, request: Request, response: Response) -> AuthView:
        await _throttle(
            request, "login", settings.login_rate_limit, settings.login_rate_window_seconds
        )
        account = await accounts.by_email(_normalize_email(body.email))
        if account is None or not verify_password(body.password, account.password_hash):
            _logger.warning("login failed (bad credentials)")
            raise HTTPException(401, "invalid email or password")
        set_session_cookie(
            response, issue_token(account.id, signing_key, int(time.time())), settings
        )
        _logger.info("login ok account=%s", account.id)
        return AuthView(
            business_id=str(account.business_id) if account.business_id else "",
            email=account.email,
            role=account.role.value,
        )

    @router.post("/api/logout")
    async def logout(request: Request, response: Response) -> dict[str, bool]:
        # Real revocation: bump the cutoff so every token issued so far (this device and others)
        # stops being accepted, not just clear the cookie in this browser.
        token = request.cookies.get(SESSION_COOKIE, "")
        account = await _verified_account(
            token, accounts, signing_key, settings.token_max_age_seconds
        )
        if account is not None:
            await accounts.upsert(replace(account, sessions_valid_after=int(time.time())))
            _logger.info("logout account=%s (sessions revoked)", account.id)
        clear_session_cookie(response, settings)
        return {"ok": True}

    @router.post("/api/account/password")
    async def change_password(
        body: PasswordChangeInput, request: Request, response: Response
    ) -> dict[str, bool]:
        token = request.cookies.get(SESSION_COOKIE, "")
        account = await _verified_account(
            token, accounts, signing_key, settings.token_max_age_seconds
        )
        if account is None:
            raise HTTPException(401, "not authenticated")
        if not verify_password(body.current_password, account.password_hash):
            _logger.warning("password change rejected: wrong current password (%s)", account.id)
            raise HTTPException(403, "current password is incorrect")
        now = int(time.time())
        await accounts.upsert(
            replace(
                account,
                password_hash=hash_password(body.new_password),
                sessions_valid_after=now,
            )
        )
        # Keep THIS session alive with a fresh token (issued at the cutoff); revoke all others.
        set_session_cookie(response, issue_token(str(account.id), signing_key, now), settings)
        _logger.info("password changed account=%s (other sessions revoked)", account.id)
        return {"ok": True}

    return router


async def _verified_account(
    token: str, accounts: AccountRepository, key: str, max_age: int
) -> Account | None:
    """The account behind a valid, non-revoked token, or None.

    Rejects a token whose issue time predates the account's ``sessions_valid_after`` cutoff (set on
    logout / password change), so those actions actually revoke the account's existing sessions.
    """
    claims = verify_token(token, key, now=int(time.time()), max_age=max_age)
    if claims is None:
        return None
    account = await accounts.get(AccountId(claims.account_id))
    if account is None or claims.issued_at < account.sessions_valid_after:
        return None
    return account


def build_me_router(accounts: AccountRepository, settings: Settings) -> APIRouter:
    """The signed-in identity (`GET /api/me`), the single source of the caller's role for the
    client. Separate from the auth actions so each router stays one responsibility."""
    router = APIRouter()
    signing_key = session_signing_key(settings.secret_key)

    @router.get("/api/me")
    async def me(request: Request) -> MeView:
        token = request.cookies.get(SESSION_COOKIE, "")
        account = await _verified_account(
            token, accounts, signing_key, settings.token_max_age_seconds
        )
        if account is None:
            raise HTTPException(401, "not authenticated")
        return MeView(
            email=account.email,
            business_id=str(account.business_id) if account.business_id else None,
            role=account.role.value,
        )

    return router


def make_owner_guard(
    accounts: AccountRepository, key: str, max_age: int = 0
) -> Callable[[str, str, str], Awaitable[None]]:
    """A dependency that requires the caller's token to own the path's business.

    The token comes from the HttpOnly session cookie; the ``Authorization: Bearer`` header is
    accepted as a fallback (server-to-server / migration). Rejections are logged.
    """

    async def guard(
        business_id: str,
        session: str = Cookie(default="", alias=SESSION_COOKIE),
        authorization: str = Header(default=""),
    ) -> None:
        token = session or authorization.removeprefix("Bearer ").strip()
        account = await _verified_account(token, accounts, key, max_age)
        if account is None:
            _logger.warning(
                "auth rejected: missing/invalid/expired/revoked token (business=%s)", business_id
            )
            raise HTTPException(401, "not authenticated")
        if str(account.business_id) != business_id:
            _logger.warning("auth rejected: token does not own business=%s", business_id)
            raise HTTPException(403, "not your business")

    return guard


def make_admin_guard(
    accounts: AccountRepository, key: str, max_age: int = 0
) -> Callable[..., Awaitable[None]]:
    """A dependency that requires the caller to be an admin (ADR-0012).

    Cross-tenant: unlike the owner guard it does not scope to a path business_id. Reuses the
    same HttpOnly session cookie / Bearer token; rejections are logged without PII.
    """

    async def guard(
        session: str = Cookie(default="", alias=SESSION_COOKIE),
        authorization: str = Header(default=""),
    ) -> None:
        token = session or authorization.removeprefix("Bearer ").strip()
        account = await _verified_account(token, accounts, key, max_age)
        if account is None:
            _logger.warning("admin auth rejected: missing/invalid/expired/revoked token")
            raise HTTPException(401, "not authenticated")
        if account.role is not UserRole.ADMIN:
            _logger.warning("admin auth rejected: account is not an admin (account=%s)", account.id)
            raise HTTPException(403, "admin only")

    return guard
