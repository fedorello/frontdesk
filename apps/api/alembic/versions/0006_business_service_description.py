"""Free-text descriptions for business and service.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-26
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE business ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE service ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE business DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE service DROP COLUMN IF EXISTS description")
