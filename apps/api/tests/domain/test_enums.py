"""Tests for closed domain value sets."""

from frontdesk.domain.enums import Channel, UserRole


def test_channel_includes_voice() -> None:
    assert Channel.VOICE.value == "voice"
    assert Channel("voice") is Channel.VOICE


def test_user_role_has_owner_and_admin_values() -> None:
    assert UserRole.OWNER.value == "owner"
    assert UserRole.ADMIN.value == "admin"


def test_user_role_parses_from_string() -> None:
    assert UserRole("admin") is UserRole.ADMIN
    assert UserRole("owner") is UserRole.OWNER
