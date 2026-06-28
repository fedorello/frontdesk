"""The real Google OAuth client: posts the code and reads the id_token claims."""

import base64
import json

import httpx

from frontdesk.infrastructure.google_oauth import HttpGoogleOAuthClient, _decode_id_token


def _id_token(claims: dict[str, object]) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{payload}.signature"


def test_decode_id_token_reads_claims() -> None:
    claims = _decode_id_token(
        _id_token({"email": "a@x.com", "email_verified": True, "name": "Ann"})
    )
    assert claims["email"] == "a@x.com"
    assert claims["email_verified"] is True


async def test_exchange_code_posts_and_parses() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        token = _id_token(
            {
                "email": "b@x.com",
                "email_verified": True,
                "name": "Bob",
                "aud": "cid",  # must match the client id
                "iss": "https://accounts.google.com",
            }
        )
        return httpx.Response(200, json={"id_token": token})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = HttpGoogleOAuthClient("cid", "secret", "https://api.test/cb", http)
        identity = await client.exchange_code("the-code")

    assert identity.email == "b@x.com"
    assert identity.email_verified is True
    assert identity.name == "Bob"
    assert "oauth2.googleapis.com/token" in captured["url"]
    assert "code=the-code" in captured["body"]
    assert "client_secret=secret" in captured["body"]


async def test_exchange_code_rejects_wrong_audience() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        # An id_token minted for a DIFFERENT client must be rejected.
        token = _id_token(
            {"email": "b@x.com", "email_verified": True, "aud": "other-client", "iss": "x"}
        )
        return httpx.Response(200, json={"id_token": token})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = HttpGoogleOAuthClient("cid", "secret", "https://api.test/cb", http)
        try:
            await client.exchange_code("the-code")
            raise AssertionError("expected aud/iss validation to fail")
        except ValueError:
            pass
