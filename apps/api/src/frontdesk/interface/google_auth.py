"""Sign in with Google (OAuth 2.0 authorization-code flow).

``/start`` redirects to Google; ``/callback`` exchanges the code, finds-or-creates the owner's
account and business, issues our session token, and bounces back to the dashboard. The Google
client secret never leaves the server.
"""

import time
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from frontdesk.application.ports import (
    Account,
    AccountRepository,
    BusinessRepository,
    GoogleOAuthClient,
    IdGenerator,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import AccountId, BusinessId
from frontdesk.domain.models import Business
from frontdesk.infrastructure.security import issue_token, verify_token

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_STATE_MAX_AGE = 600  # the round-trip to Google should take well under 10 minutes
_PLACEHOLDER_BUSINESS_NAME = "My business"  # the owner renames it in Settings
_FOUND = 302


def build_google_auth_router(
    oauth: GoogleOAuthClient,
    accounts: AccountRepository,
    businesses: BusinessRepository,
    ids: IdGenerator,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()
    enabled = bool(settings.google_client_id and settings.google_redirect_uri)

    def _back(path: str) -> RedirectResponse:
        return RedirectResponse(f"{settings.dashboard_url.rstrip('/')}{path}", status_code=_FOUND)

    @router.get("/api/auth/google/start")
    async def start() -> RedirectResponse:
        if not enabled:
            return _back("/login?error=google")
        state = issue_token(ids.new(), settings.secret_key, int(time.time()))
        params = urlencode(
            {
                "client_id": settings.google_client_id,
                "redirect_uri": settings.google_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return RedirectResponse(f"{_AUTH_ENDPOINT}?{params}", status_code=_FOUND)

    @router.get("/api/auth/google/callback")
    async def callback(code: str = "", state: str = "", error: str = "") -> RedirectResponse:
        if not enabled or error or not code:
            return _back("/login?error=google")
        if (
            verify_token(state, settings.secret_key, now=int(time.time()), max_age=_STATE_MAX_AGE)
            is None
        ):
            return _back("/login?error=google")
        identity = await oauth.exchange_code(code)
        if not identity.email or not identity.email_verified:
            return _back("/login?error=google")

        account = await accounts.by_email(identity.email)
        if account is None:
            business_id = BusinessId(ids.new())
            await businesses.upsert(
                Business(
                    business_id,
                    _PLACEHOLDER_BUSINESS_NAME,
                    "UTC",
                    owner_name=identity.name,
                )
            )
            account = Account(AccountId(ids.new()), identity.email, "", business_id)
            await accounts.upsert(account)

        token = issue_token(account.id, settings.secret_key, int(time.time()))
        query = urlencode(
            {
                "token": token,
                "business_id": str(account.business_id),
                "name": identity.name,
                "email": identity.email,
                "avatar": identity.picture,
            }
        )
        return _back(f"/auth/callback?{query}")

    return router
