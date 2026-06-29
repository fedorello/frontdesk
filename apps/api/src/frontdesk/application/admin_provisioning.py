"""Promote accounts to the admin role from an allowlist (ADR-0012).

Out-of-band provisioning: the request path never grants admin. This is run deliberately via
scripts/promote_admin.py (`make promote-admin`). Idempotent — re-running promotes nothing new.
"""

from collections.abc import Iterable
from dataclasses import replace

from frontdesk.application.ports import AccountRepository
from frontdesk.domain.enums import UserRole


def parse_admin_emails(raw: str) -> list[str]:
    """Split a comma-separated allowlist into normalized, lowercased emails (matching login)."""
    return [email.strip().lower() for email in raw.split(",") if email.strip()]


async def promote_admins(accounts: AccountRepository, emails: Iterable[str]) -> list[str]:
    """Set role=ADMIN on each existing account whose email is listed.

    Returns the emails newly promoted; an unknown email or an already-admin account is skipped,
    so the operation is idempotent.
    """
    promoted: list[str] = []
    for email in emails:
        account = await accounts.by_email(email)
        if account is None or account.role is UserRole.ADMIN:
            continue
        await accounts.upsert(replace(account, role=UserRole.ADMIN))
        promoted.append(email)
    return promoted
