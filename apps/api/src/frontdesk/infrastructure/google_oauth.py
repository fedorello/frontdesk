"""Google OAuth client: exchange an authorization code for the user's identity."""

import base64
import binascii
import json
import logging

import httpx

from frontdesk.application.ports import GoogleIdentity

_logger = logging.getLogger("frontdesk.google")

_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"
_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})


def _decode_id_token(id_token: str) -> dict[str, object]:
    # The id_token comes straight from Google's token endpoint over TLS, so its claims are
    # trustworthy without re-verifying the JWT signature (per Google's own guidance).
    parts = id_token.split(".")
    if len(parts) != 3:  # noqa: PLR2004 — header.payload.signature
        raise ValueError("malformed id_token")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_b64 + padding)
        return dict(json.loads(raw))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("undecodable id_token") from exc


class HttpGoogleOAuthClient:
    def __init__(
        self, client_id: str, client_secret: str, redirect_uri: str, http: httpx.AsyncClient
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http

    async def exchange_code(self, code: str) -> GoogleIdentity:
        response = await self._http.post(
            _TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        claims = _decode_id_token(str(response.json()["id_token"]))
        # Pin the token to THIS app: reject an id_token minted for another client or issuer.
        if claims.get("aud") != self._client_id or claims.get("iss") not in _ISSUERS:
            raise ValueError("id_token failed audience/issuer validation")
        return GoogleIdentity(
            email=str(claims.get("email", "")),
            email_verified=bool(claims.get("email_verified", False)),
            name=str(claims.get("name", "")),
            picture=str(claims.get("picture", "")),
        )


class HttpGoogleCredentialVerifier:
    """Verifies a Google Identity Services credential via Google's tokeninfo endpoint.

    The credential arrives from the browser (not over a trusted TLS channel from Google), so we
    have Google re-check the signature at tokeninfo, then pin the audience/issuer and require a
    verified email. Returns None on any failure — the caller treats that as unauthorized.
    """

    def __init__(self, client_id: str, http: httpx.AsyncClient) -> None:
        self._client_id = client_id
        self._http = http

    async def verify(self, credential: str) -> GoogleIdentity | None:
        response = await self._http.get(_TOKENINFO_ENDPOINT, params={"id_token": credential})
        if response.status_code != 200:  # noqa: PLR2004 — Google returns 400 for an invalid token
            _logger.info(
                "demo google credential rejected: tokeninfo status=%s", response.status_code
            )
            return None
        claims = response.json()
        # tokeninfo returns email_verified as the string "true"/"false".
        verified = str(claims.get("email_verified", "")).lower() == "true"
        if (
            claims.get("aud") != self._client_id
            or claims.get("iss") not in _ISSUERS
            or not verified
        ):
            _logger.info("demo google credential rejected: audience/issuer/email_verified")
            return None
        return GoogleIdentity(
            email=str(claims.get("email", "")),
            email_verified=True,
            name=str(claims.get("name", "")),
            picture=str(claims.get("picture", "")),
        )
