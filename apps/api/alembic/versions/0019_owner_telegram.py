"""Owner Telegram notifications: the link binding + one-time link codes.

Idempotent (CREATE TABLE IF NOT EXISTS): a fresh database already has these from schema.py;
an existing one gets them here. See docs/OWNER_TELEGRAM_NOTIFICATIONS.md.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-29
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_OWNER_TELEGRAM_LINK = """
CREATE TABLE IF NOT EXISTS owner_telegram_link (
    business_id text PRIMARY KEY REFERENCES business(id) ON DELETE CASCADE,
    chat_id text NOT NULL,
    telegram_name text NOT NULL,
    notifications_enabled boolean NOT NULL DEFAULT true,
    linked_at timestamptz NOT NULL DEFAULT now()
)
"""

_TELEGRAM_LINK_CODE = """
CREATE TABLE IF NOT EXISTS telegram_link_code (
    code text PRIMARY KEY,
    business_id text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
    chat_id text NOT NULL,
    telegram_name text NOT NULL,
    expires_at timestamptz NOT NULL,
    used boolean NOT NULL DEFAULT false
)
"""


def upgrade() -> None:
    op.execute(_OWNER_TELEGRAM_LINK)
    op.execute(_TELEGRAM_LINK_CODE)
    op.execute("CREATE INDEX IF NOT EXISTS link_code_expiry ON telegram_link_code (expires_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telegram_link_code")
    op.execute("DROP TABLE IF EXISTS owner_telegram_link")
