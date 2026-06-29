"""Row-creation timestamps for analytics (ADR-0012).

Adds created_at to account, appointment, and customer so the dashboard can chart signups,
bookings, and new customers over time. Persistence-only (not on the domain models), like the
existing approval.created_at. Idempotent (ADD COLUMN IF NOT EXISTS); a fresh database already
has these from schema.py.

Backfill caveat: existing rows get now() as their created_at, so pre-migration history collapses
onto the migration date. Charts are accurate from here forward.

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-29
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

_TABLES = ("account", "appointment", "customer")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "
            "created_at timestamptz NOT NULL DEFAULT now()"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS created_at")
