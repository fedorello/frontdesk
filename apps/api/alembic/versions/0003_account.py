"""Owner accounts.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-26
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_ACCOUNT = """
CREATE TABLE IF NOT EXISTS account (
    id text PRIMARY KEY,
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    business_id text REFERENCES business(id)
)
"""


def upgrade() -> None:
    op.execute(_ACCOUNT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS account")
