"""Real-Postgres round-trips for the entitlement + demo-lead adapters."""

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.domain.entitlements import DemoLead, Entitlement
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.ids import BusinessId, DemoLeadId, FeatureKey
from frontdesk.infrastructure.postgres.entitlements import (
    SqlDemoLeadRepository,
    SqlEntitlementRepository,
)

BIZ = BusinessId("biz")  # seeded by the integration conftest
VOICE = FeatureKey("voice_receptionist")
REQUESTED_AT = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 7, 2, 10, 30, tzinfo=UTC)


async def test_save_then_get_round_trips_all_fields(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlEntitlementRepository(sessionmaker)
    approved = Entitlement.requested(BIZ, VOICE, REQUESTED_AT).approve(DECIDED_AT)

    await repo.save(approved)
    loaded = await repo.get(BIZ, VOICE)

    assert loaded == approved  # status + both timestamps survive the round trip


async def test_active_features_and_upsert_reflect_status(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlEntitlementRepository(sessionmaker)

    await repo.save(Entitlement.requested(BIZ, VOICE, REQUESTED_AT))
    assert await repo.active_features(BIZ) == frozenset()  # requested is not active

    await repo.save(Entitlement.requested(BIZ, VOICE, REQUESTED_AT).approve(DECIDED_AT))
    assert await repo.active_features(BIZ) == frozenset({VOICE})  # upsert flipped it active


async def test_directory_views_pending_and_for_business(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = SqlEntitlementRepository(sessionmaker)
    await repo.save(Entitlement.requested(BIZ, VOICE, REQUESTED_AT))

    pending = await repo.pending()
    assert [(e.business_id, e.status) for e in pending] == [(BIZ, EntitlementStatus.REQUESTED)]
    assert len(await repo.for_business(BIZ)) == 1


async def test_demo_lead_is_recorded(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await SqlDemoLeadRepository(sessionmaker).record(
        DemoLead(DemoLeadId("lead-1"), "caller@example.com", VOICE, DECIDED_AT)
    )

    async with sessionmaker() as session:
        email = (
            await session.execute(text("SELECT email FROM demo_lead WHERE id = 'lead-1'"))
        ).scalar_one()
    assert email == "caller@example.com"
