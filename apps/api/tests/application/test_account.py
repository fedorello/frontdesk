"""Tests for the Account DTO and its role default (ADR-0012)."""

from frontdesk.application.ports import Account
from frontdesk.domain.enums import UserRole
from frontdesk.domain.ids import AccountId, BusinessId


def test_account_defaults_to_owner_role() -> None:
    account = Account(AccountId("a1"), "owner@example.com", "hash", BusinessId("b1"))

    assert account.role is UserRole.OWNER


def test_admin_account_owns_no_business() -> None:
    admin = Account(AccountId("a2"), "ops@example.com", "hash", role=UserRole.ADMIN)

    assert admin.business_id is None
    assert admin.role is UserRole.ADMIN
