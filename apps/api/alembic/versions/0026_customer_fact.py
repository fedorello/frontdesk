"""Customer memory: remembered facts per customer (docs/design/customer-memory.md).

Idempotent (IF NOT EXISTS): a fresh database already has the table from schema.py; an existing one
gets it here. One row per fact, upsert on the primary key.

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-02
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS customer_fact (
            business_id text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
            customer_id text NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
            key text NOT NULL,
            value text NOT NULL,
            updated_at timestamptz NOT NULL,
            PRIMARY KEY (business_id, customer_id, key)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_fact CASCADE")
