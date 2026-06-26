"""Encryption of stored secrets at rest (ADR-0009).

``FernetCipher`` is the local/self-host adapter (authenticated symmetric encryption,
key from the environment). A KMS-backed adapter can replace it behind the same
``SecretCipher`` port without touching call sites.
"""

from cryptography.fernet import Fernet


class FernetCipher:
    """Authenticated symmetric encryption (Fernet / AES) with an env-provided key."""

    def __init__(self, key: str) -> None:
        if not key:
            raise ValueError("FRONTDESK_SECRET_KEY is required to encrypt stored secrets")
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    @staticmethod
    def generate_key() -> str:
        """A fresh urlsafe-base64 key — for `FRONTDESK_SECRET_KEY`."""
        return Fernet.generate_key().decode()
