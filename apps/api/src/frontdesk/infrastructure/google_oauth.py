"""Google OAuth client: exchange an authorization code for the user's identity."""

import base64
import binascii
import json

import httpx

from frontdesk.application.ports import GoogleIdentity

_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
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
