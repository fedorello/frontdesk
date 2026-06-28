"""Give every business a group and repoint services at it.

Before service groups, businesses created via /signup or Google never got a resource, and the
old UI hard-coded every service's resource_ids to the global id "main" — so those services
pointed at a non-existent (or another tenant's) group. That breaks availability and group
display. This backfill: (1) creates a default group for any business without one, and
(2) repoints services whose group is missing or belongs to another business to their own
business's group. Idempotent. See docs/SERVICE_GROUPS.md.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_DEFAULT_HOURS = (
    '[{"weekday":0,"opens":"09:00:00","closes":"17:00:00"},'
    '{"weekday":1,"opens":"09:00:00","closes":"17:00:00"},'
    '{"weekday":2,"opens":"09:00:00","closes":"17:00:00"},'
    '{"weekday":3,"opens":"09:00:00","closes":"17:00:00"},'
    '{"weekday":4,"opens":"09:00:00","closes":"17:00:00"}]'
)


def upgrade() -> None:
    # The schedule is a bound parameter: its ":00"/":0" would otherwise be read as bind names.
    op.execute(
        sa.text(
            "INSERT INTO resource (id, business_id, name, working_hours) "
            "SELECT 'grp-' || b.id, b.id, 'Main', CAST(:hours AS jsonb) "
            "FROM business b "
            "WHERE NOT EXISTS (SELECT 1 FROM resource r WHERE r.business_id = b.id)"
        ).bindparams(hours=_DEFAULT_HOURS)
    )
    op.execute(
        """
        UPDATE service s
        SET resource_ids = jsonb_build_array(
            (SELECT r.id FROM resource r WHERE r.business_id = s.business_id ORDER BY r.id LIMIT 1)
        )
        WHERE NOT EXISTS (
            SELECT 1 FROM resource r
            WHERE r.id = (s.resource_ids ->> 0) AND r.business_id = s.business_id
        )
        """
    )


def downgrade() -> None:
    # Data repair isn't cleanly reversible (the old resource_ids are not recoverable).
    pass
