"""Purpose-separated subkeys derived from the master ``FRONTDESK_SECRET_KEY`` (HKDF-SHA256).

One env var, three independent keys — so encryption, session-token signing, and OAuth-state
signing never share key material (hardening plan §3.4). Each subkey is bound to a distinct
``info`` label, so they're cryptographically independent even though they come from one master.
"""

import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def _derive(master: str, info: bytes, length: int = 32) -> bytes:
    # Fail closed: an empty master would derive deterministic, attacker-known subkeys (forgeable
    # session/OAuth tokens). Guard here so EVERY consumer is safe, not only the cipher.
    if not master:
        raise ValueError("FRONTDESK_SECRET_KEY is required and must not be empty")
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=info).derive(
        master.encode()
    )


def session_signing_key(master: str) -> str:
    """HMAC key (hex) for owner session tokens."""
    return _derive(master, b"frontdesk/session").hex()


def oauth_state_key(master: str) -> str:
    """HMAC key (hex) for the OAuth CSRF state token."""
    return _derive(master, b"frontdesk/oauth-state").hex()


def encryption_key(master: str) -> str:
    """A Fernet key (urlsafe base64) for encrypting stored secrets."""
    return base64.urlsafe_b64encode(_derive(master, b"frontdesk/fernet")).decode()
