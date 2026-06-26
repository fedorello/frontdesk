"""Password hashing (PBKDF2-HMAC-SHA256) and signed auth tokens (HMAC). Stdlib only."""

import base64
import hashlib
import hmac
import secrets

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, derived_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(derived_b64)
    except ValueError:
        return False
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return hmac.compare_digest(derived, expected)


def issue_token(account_id: str, key: str, issued_at: int) -> str:
    payload = f"{account_id}:{issued_at}"
    signature = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def verify_token(token: str, key: str, *, now: int, max_age: int) -> str | None:
    """Return the account id if the token's signature is valid and not expired.

    ``max_age`` of 0 disables expiry. ``now``/``issued_at`` are unix epoch seconds.
    """
    try:
        account_id, issued_at_raw, signature = (
            base64.urlsafe_b64decode(token.encode()).decode().rsplit(":", 2)
        )
        issued_at = int(issued_at_raw)
    except ValueError:
        return None
    payload = f"{account_id}:{issued_at}"
    expected = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if max_age > 0 and now - issued_at > max_age:
        return None
    return account_id
