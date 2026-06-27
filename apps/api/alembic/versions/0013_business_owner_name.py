"""The business owner's display name, shown to customers when the owner replies.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-27
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE business ADD COLUMN IF NOT EXISTS owner_name text NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE business DROP COLUMN IF EXISTS owner_name")
