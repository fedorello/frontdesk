"""Per-business daily usage counter (managed-default cost control).

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-26
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_USAGE = """
CREATE TABLE IF NOT EXISTS usage_counter (
    business_id text NOT NULL REFERENCES business(id),
    day text NOT NULL,
    count integer NOT NULL DEFAULT 0,
    PRIMARY KEY (business_id, day)
)
"""


def upgrade() -> None:
    op.execute(_USAGE)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_counter")
