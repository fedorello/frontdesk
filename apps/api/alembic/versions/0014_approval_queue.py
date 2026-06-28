"""DB-backed approval queue (Airlock dogfood) — restart-safe and cross-process.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-28
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE approval (
            request_id text PRIMARY KEY,
            business_id text NOT NULL REFERENCES business(id),
            tool text NOT NULL,
            summary text NOT NULL,
            risk text NOT NULL,
            args jsonb NOT NULL DEFAULT '{}'::jsonb,
            status text NOT NULL DEFAULT 'pending',
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX approval_pending ON approval (business_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS approval CASCADE")
