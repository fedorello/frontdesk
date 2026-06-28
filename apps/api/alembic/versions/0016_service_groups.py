"""Service groups: the schedule moves from each service onto its group (the resource).

Backfills each group's working_hours from its member services (the schedule the owner had
configured per service), then drops service.working_hours. See docs/SERVICE_GROUPS.md.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-28
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded by the column's existence so it's a one-time backfill + drop on an existing DB
    # and a clean no-op on a fresh DB (where the current schema never creates the column).
    # For each group, take the schedule of its member service with the most windows (the most
    # permissive, deterministic choice); the owner can refine it in the new Groups UI.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'service' AND column_name = 'working_hours'
            ) THEN
                UPDATE resource r
                SET working_hours = chosen.working_hours
                FROM (
                    SELECT DISTINCT ON (s.resource_ids ->> 0)
                           (s.resource_ids ->> 0) AS group_id, s.working_hours
                    FROM service s
                    WHERE jsonb_array_length(s.working_hours) > 0
                    ORDER BY (s.resource_ids ->> 0), jsonb_array_length(s.working_hours) DESC
                ) AS chosen
                WHERE r.id = chosen.group_id;

                ALTER TABLE service DROP COLUMN working_hours;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE service ADD COLUMN IF NOT EXISTS working_hours jsonb NOT NULL DEFAULT '[]'"
    )
