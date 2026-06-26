"""FernetCipher encrypts stored secrets at rest and decrypts them back."""

import pytest

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
