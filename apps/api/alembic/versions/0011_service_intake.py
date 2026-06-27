"""Per-service intake fields and the answers captured on each appointment.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-27
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE service ADD COLUMN IF NOT EXISTS intake_fields jsonb NOT NULL DEFAULT '[]'")
    op.execute("ALTER TABLE appointment ADD COLUMN IF NOT EXISTS intake jsonb NOT NULL DEFAULT '[]'")


def downgrade() -> None:
    op.execute("ALTER TABLE service DROP COLUMN IF EXISTS intake_fields")
    op.execute("ALTER TABLE appointment DROP COLUMN IF EXISTS intake")
