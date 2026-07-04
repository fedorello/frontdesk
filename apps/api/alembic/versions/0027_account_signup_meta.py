"""Account sign-up origin: client IP + resolved country, for the operator's admin view.

Idempotent (ADD COLUMN IF NOT EXISTS): a fresh database already has the columns from schema.py; an
existing one gets them here. Captured once at sign-up; empty when unknown.

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-04
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE account ADD COLUMN IF NOT EXISTS signup_ip text NOT NULL DEFAULT ''")
    op.execute(
        "ALTER TABLE account ADD COLUMN IF NOT EXISTS signup_country text NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE account DROP COLUMN IF EXISTS signup_country")
    op.execute("ALTER TABLE account DROP COLUMN IF EXISTS signup_ip")
