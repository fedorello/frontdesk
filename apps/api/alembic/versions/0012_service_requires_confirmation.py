"""Per-service flag: do bookings need the owner's confirmation, or auto-confirm.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-27
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE service ADD COLUMN IF NOT EXISTS "
        "requires_confirmation boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE service DROP COLUMN IF EXISTS requires_confirmation")
