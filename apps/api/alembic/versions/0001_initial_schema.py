"""Initial schema.

Revision ID: 0001
Revises:
Create Date: 2026-06-25

Runs the single source-of-truth DDL (including the btree_gist extension and the
no-double-book exclusion constraint) so the migration and the tests never drift.
"""

from alembic import op

from frontdesk.infrastructure.postgres.schema import CREATE_STATEMENTS, DROP_STATEMENTS

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in CREATE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DROP_STATEMENTS:
        op.execute(statement)
