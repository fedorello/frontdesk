"""FernetCipher encrypts stored secrets at rest and decrypts them back."""

import pytest
from cryptography.fernet import Fernet

from frontdesk.infrastructure.keys import (
    encryption_key,
    oauth_state_key,
    session_signing_key,
)
from frontdesk.infrastructure.secrets import FernetCipher


def test_roundtrip_hides_the_plaintext() -> None:
    cipher = FernetCipher(FernetCipher.generate_key())

    token = cipher.encrypt("sk-secret-123")

    assert token != "sk-secret-123"  # stored value is ciphertext
    assert cipher.decrypt(token) == "sk-secret-123"


def test_each_encryption_is_distinct() -> None:
    cipher = FernetCipher(FernetCipher.generate_key())

    assert cipher.encrypt("x") != cipher.encrypt("x")  # Fernet randomises


def test_a_key_is_required() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        FernetCipher("")


def test_hkdf_subkeys_are_distinct_and_stable() -> None:
    master = FernetCipher.generate_key()
    sign, state, enc = (
        session_signing_key(master),
        oauth_state_key(master),
        encryption_key(master),
    )
    assert len({sign, state, enc}) == 3  # purpose-separated, all distinct
    assert session_signing_key(master) == sign  # deterministic from the master


def test_cipher_still_decrypts_legacy_ciphertext() -> None:
    # Data encrypted under the RAW master key (pre-HKDF) must still decrypt, so existing
    # stored bot tokens / LLM keys keep working after the key-separation change.
    master = FernetCipher.generate_key()
    legacy = Fernet(master.encode()).encrypt(b"old-secret").decode()

    cipher = FernetCipher(master)

    assert cipher.decrypt(legacy) == "old-secret"  # legacy fallback
    assert cipher.decrypt(cipher.encrypt("new-secret")) == "new-secret"  # derived key
