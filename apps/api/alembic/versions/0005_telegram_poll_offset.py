"""Telegram poller offset cursor.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE telegram_bot ADD COLUMN IF NOT EXISTS last_update_id bigint NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE telegram_bot DROP COLUMN IF EXISTS last_update_id")
