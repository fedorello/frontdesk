"""The session cookie: the auth token rides in an HttpOnly cookie, never JS-readable.

Keeping the token out of JavaScript (and out of redirect URLs) closes the two biggest
session-theft vectors — an XSS reading localStorage, and the token leaking via browser
history / Referer / proxy logs.
"""

from typing import Literal

from fastapi import Response

from frontdesk.core.settings import Settings

SESSION_COOKIE = "tovayo.session"
OAUTH_STATE_COOKIE = "tovayo.oauth_state"
OAUTH_STATE_MAX_AGE = 600  # the Google round-trip should finish well within 10 minutes
# Same-site: the dashboard and API are same-site (*.tovayo.com), so Lax is enough.
_SAME_SITE: Literal["lax"] = "lax"


def _secure(settings: Settings) -> bool:
    # Secure (HTTPS-only) in production; relaxed on plain-HTTP localhost so dev still works.
    return settings.public_url.startswith("https://")


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """Attach the HttpOnly session cookie carrying the auth token."""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.token_max_age_seconds or None,
        httponly=True,
        secure=_secure(settings),
        samesite=_SAME_SITE,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """Remove the session cookie (logout)."""
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_secure(settings), samesite=_SAME_SITE)


def set_oauth_state_cookie(response: Response, state: str, settings: Settings) -> None:
    """Bind the OAuth ``state`` to this browser so the callback can't be replayed cross-session."""
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        secure=_secure(settings),
        samesite=_SAME_SITE,
        path="/",
    )


def clear_oauth_state_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        OAUTH_STATE_COOKIE, path="/", secure=_secure(settings), samesite=_SAME_SITE
    )
