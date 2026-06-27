"""Online (no physical address) flag for a business.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-26
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE business ADD COLUMN IF NOT EXISTS online boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE business DROP COLUMN IF EXISTS online")
