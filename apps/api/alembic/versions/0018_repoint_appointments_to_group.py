"""Repoint existing appointments to their service's current group.

Migration 0017 repointed services to their own group but left appointments on the old (often
shared "main") resource_id. Availability is computed per group, so those bookings stopped
blocking their slot — a taken time looked free and could be double-booked. This repoints every
non-cancelled appointment whose resource_id drifted from its service's group.

Conflict-free: the old global resource already enforced no overlapping appointments (the
exclusion constraint), so each per-group subset is overlap-free too. Idempotent.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-28
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE appointment a
        SET resource_id = sub.group_id
        FROM (SELECT s.id AS service_id, (s.resource_ids ->> 0) AS group_id FROM service s) sub
        WHERE a.service_id = sub.service_id
          AND a.status <> 'cancelled'
          AND a.resource_id <> sub.group_id
          AND sub.group_id IS NOT NULL
        """
    )


def downgrade() -> None:
    pass  # the original resource_ids are not recoverable
