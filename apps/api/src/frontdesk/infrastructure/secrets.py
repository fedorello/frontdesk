"""Encryption of stored secrets at rest (ADR-0009).

``FernetCipher`` is the local/self-host adapter (authenticated symmetric encryption,
key from the environment). A KMS-backed adapter can replace it behind the same
``SecretCipher`` port without touching call sites.
"""

from cryptography.fernet import Fernet, MultiFernet

from frontdesk.infrastructure.keys import encryption_key


class FernetCipher:
    """Authenticated symmetric encryption (Fernet / AES) with an env-provided key.

    Encrypts under a derived subkey (key separation, §3.4) while still decrypting data
    written under the raw master key — a backward-compatible migration. ``MultiFernet``
    encrypts with the first key (derived) and decrypts with any; existing ciphertext falls
    back to the legacy key, and re-encrypting moves it onto the derived key over time.
    """

    def __init__(self, key: str) -> None:
        if not key:
            raise ValueError("FRONTDESK_SECRET_KEY is required to encrypt stored secrets")
        derived = Fernet(encryption_key(key).encode())
        legacy = Fernet(key.encode())
        self._fernet = MultiFernet([derived, legacy])

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    @staticmethod
    def generate_key() -> str:
        """A fresh urlsafe-base64 key — for `FRONTDESK_SECRET_KEY`."""
        return Fernet.generate_key().decode()
