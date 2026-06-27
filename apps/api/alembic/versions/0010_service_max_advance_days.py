"""How far ahead a service may be booked.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-27
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE service ADD COLUMN IF NOT EXISTS max_advance_days integer NOT NULL DEFAULT 30"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE service DROP COLUMN IF EXISTS max_advance_days")
