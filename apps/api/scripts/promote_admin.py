"""Promote the allowlisted accounts to the admin role (ADR-0012). Idempotent.

Reads FRONTDESK_ADMIN_EMAILS (comma-separated) and sets role=admin on those existing accounts.
Run via `make promote-admin`. The request path never grants admin; this is the only way in.
"""

import asyncio

from frontdesk.application.admin_provisioning import parse_admin_emails, promote_admins
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.postgres.adapters import SqlAccountRepository


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    emails = parse_admin_emails(settings.admin_emails)
    promoted = await promote_admins(SqlAccountRepository(sessions), emails)
    await engine.dispose()
    print(f"promoted {len(promoted)} account(s) to admin: {promoted}")


if __name__ == "__main__":
    asyncio.run(main())
