"""Owner accounts: sign up, log in, and a guard that scopes routes to the owner.

Tokens are HMAC-signed (``security.py``); one account owns one business, and the
guard rejects any request whose token doesn't own the business in the path (M4).
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Header, HTTPException
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

_MIN_PASSWORD_LENGTH = 8


class SignupInput(BaseModel):
    email: str
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)
    business_name: str
    timezone: str = "UTC"


class LoginInput(BaseModel):
    email: str
    password: str


class AuthView(BaseModel):
    token: str
    business_id: str


def build_auth_router(
    accounts: AccountRepository,
    businesses: BusinessRepository,
    ids: IdGenerator,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/signup")
    async def signup(body: SignupInput) -> AuthView:
        if await accounts.by_email(body.email) is not None:
            raise HTTPException(409, "email already registered")
        business_id = BusinessId(ids.new())
        await businesses.upsert(Business(business_id, body.business_name, body.timezone))
        account = Account(
            AccountId(ids.new()), body.email, hash_password(body.password), business_id
        )
        await accounts.upsert(account)
        token = issue_token(account.id, settings.secret_key, int(time.time()))
        return AuthView(token=token, business_id=business_id)

    @router.post("/api/login")
    async def login(body: LoginInput) -> AuthView:
        account = await accounts.by_email(body.email)
        if account is None or not verify_password(body.password, account.password_hash):
            raise HTTPException(401, "invalid email or password")
        return AuthView(
            token=issue_token(account.id, settings.secret_key, int(time.time())),
            business_id=str(account.business_id),
        )

    return router


def make_owner_guard(
    accounts: AccountRepository, key: str, max_age: int = 0
) -> Callable[[str, str], Awaitable[None]]:
    """A dependency that requires the caller's token to own the path's business."""

    async def guard(business_id: str, authorization: str = Header(default="")) -> None:
        token = authorization.removeprefix("Bearer ").strip()
        account_id = verify_token(token, key, now=int(time.time()), max_age=max_age)
        if account_id is None:
            raise HTTPException(401, "not authenticated")
        account = await accounts.get(AccountId(account_id))
        if account is None or str(account.business_id) != business_id:
            raise HTTPException(403, "not your business")

    return guard
