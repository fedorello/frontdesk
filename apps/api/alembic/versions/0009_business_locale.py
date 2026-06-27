"""The business's chosen language (drives the bot's filler phrases).

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-27
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE business ADD COLUMN IF NOT EXISTS locale text NOT NULL DEFAULT 'en'")


def downgrade() -> None:
    op.execute("ALTER TABLE business DROP COLUMN IF EXISTS locale")
