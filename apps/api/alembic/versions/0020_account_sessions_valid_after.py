"""Session revocation: account.sessions_valid_after cutoff.

Idempotent (ADD COLUMN IF NOT EXISTS): a fresh database already has the column from schema.py;
an existing one gets it here. Tokens issued before this epoch-second cutoff are rejected, so
logout and password change actually revoke existing sessions.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-29
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE account ADD COLUMN IF NOT EXISTS "
        "sessions_valid_after bigint NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE account DROP COLUMN IF EXISTS sessions_valid_after")
