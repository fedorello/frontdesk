"""Per-service weekly schedule and business address.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-26
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE service ADD COLUMN IF NOT EXISTS working_hours jsonb NOT NULL DEFAULT '[]'"
    )
    op.execute("ALTER TABLE business ADD COLUMN IF NOT EXISTS address text NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE service DROP COLUMN IF EXISTS working_hours")
    op.execute("ALTER TABLE business DROP COLUMN IF EXISTS address")
