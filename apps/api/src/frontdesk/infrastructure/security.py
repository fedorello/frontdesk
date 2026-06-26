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


def issue_token(account_id: str, key: str) -> str:
    signature = hmac.new(key.encode(), account_id.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{account_id}:{signature}".encode()).decode()


def verify_token(token: str, key: str) -> str | None:
    try:
        account_id, signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit(":", 1)
    except ValueError:
        return None
    expected = hmac.new(key.encode(), account_id.encode(), hashlib.sha256).hexdigest()
    return account_id if hmac.compare_digest(signature, expected) else None
