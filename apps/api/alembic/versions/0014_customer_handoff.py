"""Per-customer handoff flag: the owner has taken the conversation over from the assistant.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-27
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE customer ADD COLUMN IF NOT EXISTS "
        "handled_by_owner boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS handled_by_owner")
