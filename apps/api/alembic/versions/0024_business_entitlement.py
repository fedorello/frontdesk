"""Per-business premium-feature entitlements (docs/plans/premium-features-plan.md).

Idempotent (IF NOT EXISTS): a fresh database already has the table from schema.py; an existing one
gets it here. ``feature_key`` is validated against the config-driven registry in the domain, so it
is intentionally not a foreign key.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-02
"""

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS business_entitlement (
            business_id text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
            feature_key text NOT NULL,
            status text NOT NULL CHECK (status IN ('requested', 'active', 'suspended')),
            requested_at timestamptz NOT NULL,
            decided_at timestamptz NULL,
            PRIMARY KEY (business_id, feature_key)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS entitlement_status ON business_entitlement (status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS business_entitlement CASCADE")
