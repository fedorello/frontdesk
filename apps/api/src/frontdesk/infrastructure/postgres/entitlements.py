"""Postgres adapters for premium-feature entitlements and landing-demo leads.

``SqlEntitlementRepository`` backs both the hot ``EntitlementRepository`` (read + write) and the
operator ``EntitlementDirectory`` views. Mirrors the session/text-query style of ``adapters.py``.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.entitlements import DemoLead, Entitlement
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.ids import BusinessId, FeatureKey

Row = Any  # a SQLAlchemy RowMapping, matching the alias in adapters.py (§8.4: opaque DB row)


def _to_entitlement(row: Row) -> Entitlement:
    return Entitlement(
        business_id=BusinessId(row["business_id"]),
        feature_key=FeatureKey(row["feature_key"]),
        status=EntitlementStatus(row["status"]),
        requested_at=row["requested_at"],
        decided_at=row["decided_at"],
    )


class SqlEntitlementRepository:
    """Reads/writes ``business_entitlement`` — the EntitlementRepository + EntitlementDirectory."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def active_features(self, business_id: BusinessId) -> frozenset[FeatureKey]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT feature_key FROM business_entitlement "
                            "WHERE business_id = :b AND status = 'active'"
                        ),
                        {"b": str(business_id)},
                    )
                )
                .scalars()
                .all()
            )
        return frozenset(FeatureKey(key) for key in rows)

    async def get(self, business_id: BusinessId, feature_key: FeatureKey) -> Entitlement | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM business_entitlement "
                            "WHERE business_id = :b AND feature_key = :k"
                        ),
                        {"b": str(business_id), "k": str(feature_key)},
                    )
                )
                .mappings()
                .first()
            )
        return _to_entitlement(row) if row else None

    async def save(self, entitlement: Entitlement) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO business_entitlement "
                    "(business_id, feature_key, status, requested_at, decided_at) "
                    "VALUES (:b, :k, :s, :rq, :dc) "
                    "ON CONFLICT (business_id, feature_key) DO UPDATE SET "
                    "status = :s, requested_at = :rq, decided_at = :dc"
                ),
                {
                    "b": str(entitlement.business_id),
                    "k": str(entitlement.feature_key),
                    "s": entitlement.status.value,
                    "rq": entitlement.requested_at,
                    "dc": entitlement.decided_at,
                },
            )
            await session.commit()

    async def pending(self) -> tuple[Entitlement, ...]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM business_entitlement WHERE status = 'requested' "
                            "ORDER BY requested_at"
                        )
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_to_entitlement(row) for row in rows)

    async def for_business(self, business_id: BusinessId) -> tuple[Entitlement, ...]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM business_entitlement WHERE business_id = :b "
                            "ORDER BY feature_key"
                        ),
                        {"b": str(business_id)},
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_to_entitlement(row) for row in rows)


class SqlDemoLeadRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def record(self, lead: DemoLead) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO demo_lead (id, email, feature_key, created_at) "
                    "VALUES (:id, :email, :k, :at)"
                ),
                {
                    "id": str(lead.id),
                    "email": lead.email,
                    "k": str(lead.feature_key),
                    "at": lead.created_at,
                },
            )
            await session.commit()
