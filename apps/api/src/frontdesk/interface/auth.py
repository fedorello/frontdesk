"""Owner accounts: sign up, log in, log out, and a guard that scopes routes to the owner.

Tokens are HMAC-signed (``security.py``) and delivered in an HttpOnly cookie (``cookies.py``),
never in the response body or a URL. One account owns one business; the guard rejects any
request whose token doesn't own the business in the path. Security events are logged (no PII).
"""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel, Field

from frontdesk.application.ports import (
    Account,
    AccountRepository,
    BusinessRepository,
    IdGenerator,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import AccountId, BusinessId
from frontdesk.domain.models import Business
from frontdesk.infrastructure.security import (
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)
from frontdesk.interface.cookies import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_session_cookie,
)

_MIN_PASSWORD_LENGTH = 8
_logger = logging.getLogger("frontdesk.auth")


class SignupInput(BaseModel):
    email: str
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)
    business_name: str
    timezone: str = "UTC"


class LoginInput(BaseModel):
    email: str
    password: str


class AuthView(BaseModel):
    """What the client gets back — the business to scope its calls to, and the owner's email.

    The auth token is NOT here: it lives only in the HttpOnly session cookie.
    """

    business_id: str
    email: str


def build_auth_router(
    accounts: AccountRepository,
    businesses: BusinessRepository,
    ids: IdGenerator,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/signup")
    async def signup(body: SignupInput, response: Response) -> AuthView:
        if await accounts.by_email(body.email) is not None:
            raise HTTPException(409, "email already registered")
        business_id = BusinessId(ids.new())
        await businesses.upsert(Business(business_id, body.business_name, body.timezone))
        account = Account(
            AccountId(ids.new()), body.email, hash_password(body.password), business_id
        )
        await accounts.upsert(account)
        set_session_cookie(
            response, issue_token(account.id, settings.secret_key, int(time.time())), settings
        )
        _logger.info("signup account=%s business=%s", account.id, business_id)
        return AuthView(business_id=business_id, email=account.email)

    @router.post("/api/login")
    async def login(body: LoginInput, response: Response) -> AuthView:
        account = await accounts.by_email(body.email)
        if account is None or not verify_password(body.password, account.password_hash):
            _logger.warning("login failed (bad credentials)")
            raise HTTPException(401, "invalid email or password")
        set_session_cookie(
            response, issue_token(account.id, settings.secret_key, int(time.time())), settings
        )
        _logger.info("login ok account=%s", account.id)
        return AuthView(business_id=str(account.business_id), email=account.email)

    @router.post("/api/logout")
    async def logout(response: Response) -> dict[str, bool]:
        clear_session_cookie(response, settings)
        _logger.info("logout")
        return {"ok": True}

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
        account_id = verify_token(token, key, now=int(time.time()), max_age=max_age)
        if account_id is None:
            _logger.warning(
                "auth rejected: missing/invalid/expired token (business=%s)", business_id
            )
            raise HTTPException(401, "not authenticated")
        account = await accounts.get(AccountId(account_id))
        if account is None or str(account.business_id) != business_id:
            _logger.warning("auth rejected: token does not own business=%s", business_id)
            raise HTTPException(403, "not your business")

    return guard
