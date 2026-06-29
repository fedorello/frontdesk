"""Tests for out-of-band admin provisioning (ADR-0012)."""

from frontdesk.application.admin_provisioning import parse_admin_emails, promote_admins
from frontdesk.application.ports import Account
from frontdesk.domain.enums import UserRole
from frontdesk.domain.ids import AccountId, BusinessId
from frontdesk.infrastructure.memory import InMemoryAccountRepository


def test_parse_admin_emails_normalizes_and_drops_blanks() -> None:
    assert parse_admin_emails(" A@X.com , ,b@x.com ") == ["a@x.com", "b@x.com"]
    assert parse_admin_emails("") == []


async def _owner(repo: InMemoryAccountRepository, account_id: str, email: str) -> None:
    await repo.upsert(Account(AccountId(account_id), email, "h", BusinessId("b-" + account_id)))


async def test_promote_admins_promotes_listed_owners_only() -> None:
    accounts = InMemoryAccountRepository()
    await _owner(accounts, "1", "ops@x.com")
    await _owner(accounts, "2", "owner@x.com")

    promoted = await promote_admins(accounts, ["ops@x.com", "unknown@x.com"])

    assert promoted == ["ops@x.com"]  # unknown email skipped
    ops = await accounts.by_email("ops@x.com")
    owner = await accounts.by_email("owner@x.com")
    assert ops is not None
    assert owner is not None
    assert ops.role is UserRole.ADMIN
    assert owner.role is UserRole.OWNER  # not listed


async def test_promote_admins_is_idempotent() -> None:
    accounts = InMemoryAccountRepository()
    await _owner(accounts, "1", "ops@x.com")

    first = await promote_admins(accounts, ["ops@x.com"])
    second = await promote_admins(accounts, ["ops@x.com"])

    assert first == ["ops@x.com"]
    assert second == []  # already an admin → nothing to do
