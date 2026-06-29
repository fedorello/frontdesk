"""Account role: owner or admin (ADR-0012).

Idempotent (ADD COLUMN IF NOT EXISTS): a fresh database already has the column from schema.py;
an existing one gets it here. The inline CHECK whitelists the allowed roles. An admin account
owns no business and reads cross-tenant analytics.

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-29
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE account ADD COLUMN IF NOT EXISTS "
        "role text NOT NULL DEFAULT 'owner' CHECK (role IN ('owner', 'admin'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE account DROP COLUMN IF EXISTS role")
