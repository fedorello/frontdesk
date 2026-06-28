"""DB-backed approval queue (Airlock dogfood) — restart-safe and cross-process.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-28
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent (IF NOT EXISTS): a fresh DB already has it from the initial schema
    # (schema.py CREATE_STATEMENTS); an existing DB gets it added here.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS approval (
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
    op.execute("CREATE INDEX IF NOT EXISTS approval_pending ON approval (business_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS approval CASCADE")
