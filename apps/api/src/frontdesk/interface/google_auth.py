"""Sign in with Google (OAuth 2.0 authorization-code flow).

``/start`` redirects to Google; ``/callback`` exchanges the code, finds-or-creates the owner's
account and business, issues our session token, and bounces back to the dashboard. The Google
client secret never leaves the server.
"""

import hmac
import logging
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Request
from fastapi.responses import RedirectResponse

from frontdesk.application.ports import (
    Account,
    AccountRepository,
    BusinessRepository,
    GoogleOAuthClient,
    IdGenerator,
    RateLimiter,
    ResourceRepository,
)
from frontdesk.core.settings import Settings
from frontdesk.domain.ids import AccountId, BusinessId, ResourceId
from frontdesk.domain.models import Business, default_group
from frontdesk.infrastructure.keys import oauth_state_key, session_signing_key
from frontdesk.infrastructure.security import issue_token, verify_token
from frontdesk.interface.client_ip import client_ip
from frontdesk.interface.cookies import (
    OAUTH_STATE_COOKIE,
    OAUTH_STATE_MAX_AGE,
    clear_oauth_state_cookie,
    set_oauth_state_cookie,
    set_session_cookie,
)

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_PLACEHOLDER_BUSINESS_NAME = "My business"  # the owner renames it in Settings
_FOUND = 302
_logger = logging.getLogger("frontdesk.google_auth")


def build_google_auth_router(
    oauth: GoogleOAuthClient,
    accounts: AccountRepository,
    businesses: BusinessRepository,
    resources: ResourceRepository,
    ids: IdGenerator,
    settings: Settings,
    limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()
    enabled = bool(settings.google_client_id and settings.google_redirect_uri)
    state_key = oauth_state_key(settings.secret_key)  # purpose-separated signing keys (§3.4)
    signing_key = session_signing_key(settings.secret_key)

    def _back(path: str) -> RedirectResponse:
        return RedirectResponse(f"{settings.dashboard_url.rstrip('/')}{path}", status_code=_FOUND)

    @router.get("/api/auth/google/start")
    async def start(request: Request) -> RedirectResponse:
        if not enabled:
            return _back("/login?error=google")
        ip = client_ip(request, settings.trusted_proxy_hops)
        if settings.login_rate_limit and not await limiter.hit(
            f"oauth:{ip}", settings.login_rate_limit, settings.login_rate_window_seconds
        ):
            _logger.warning("rate limited: oauth ip=%s", ip)
            return _back("/login?error=google")
        state = issue_token(ids.new(), state_key, int(time.time()))
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
        redirect = RedirectResponse(f"{_AUTH_ENDPOINT}?{params}", status_code=_FOUND)
        set_oauth_state_cookie(redirect, state, settings)  # bind the state to this browser
        return redirect

    @router.get("/api/auth/google/callback")
    async def callback(
        code: str = "",
        state: str = "",
        error: str = "",
        state_cookie: str = Cookie(default="", alias=OAUTH_STATE_COOKIE),
    ) -> RedirectResponse:
        if not enabled or error or not code:
            return _back("/login?error=google")
        # State must match this browser's cookie (CSRF binding) AND be a token we signed + fresh.
        signed_ok = (
            verify_token(state, state_key, now=int(time.time()), max_age=OAUTH_STATE_MAX_AGE)
            is not None
        )
        if not (state_cookie and hmac.compare_digest(state, state_cookie) and signed_ok):
            _logger.warning("google callback: state mismatch or expired")
            return _back("/login?error=google")
        try:
            identity = await oauth.exchange_code(code)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            _logger.warning("google code exchange failed: %s", exc)
            return _back("/login?error=google")
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
            # Every business starts with one group, so services always have a valid calendar.
            await resources.upsert(default_group(business_id, ResourceId(ids.new())))
            account = Account(AccountId(ids.new()), identity.email, "", business_id)
            await accounts.upsert(account)

        token = issue_token(account.id, signing_key, int(time.time()))
        # No token in the URL — it goes in the HttpOnly cookie. Only non-secret display data.
        query = urlencode(
            {
                "business_id": str(account.business_id),
                "name": identity.name,
                "email": identity.email,
                "avatar": identity.picture,
                "role": account.role.value,
            }
        )
        redirect = _back(f"/auth/callback?{query}")
        set_session_cookie(redirect, token, settings)
        clear_oauth_state_cookie(redirect, settings)
        _logger.info("google sign-in account=%s", account.id)
        return redirect

    return router
