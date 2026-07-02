"""Landing-demo leads: a Google-signed-in visitor's email, captured to unlock the demo numbers.

Idempotent (IF NOT EXISTS): a fresh database already has the table from schema.py; an existing one
gets it here.

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-02
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS demo_lead (
            id text PRIMARY KEY,
            email text NOT NULL,
            feature_key text NOT NULL,
            created_at timestamptz NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_lead CASCADE")
