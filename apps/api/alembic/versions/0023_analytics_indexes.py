"""Aggregation indexes for the analytics dashboard (ADR-0012).

Keeps the cross-tenant GROUP BYs cheap: signups / bookings / new-customers over time, and
assistant-reply counts per day and per business. Idempotent (CREATE INDEX IF NOT EXISTS);
a fresh database already has these from schema.py.

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-29
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS account_created_at ON account (created_at)",
    "CREATE INDEX IF NOT EXISTS appointment_created_at ON appointment (created_at)",
    "CREATE INDEX IF NOT EXISTS customer_created_at ON customer (created_at)",
    "CREATE INDEX IF NOT EXISTS message_role_at ON message (role, at)",
    "CREATE INDEX IF NOT EXISTS message_business_role ON message (business_id, role)",
)
_INDEX_NAMES = (
    "account_created_at",
    "appointment_created_at",
    "customer_created_at",
    "message_role_at",
    "message_business_role",
)


def upgrade() -> None:
    for statement in _INDEXES:
        op.execute(statement)


def downgrade() -> None:
    for name in _INDEX_NAMES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
