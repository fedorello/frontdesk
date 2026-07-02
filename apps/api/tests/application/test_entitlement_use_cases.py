"""FeatureCatalog (owner view) and RequestFeature (self-serve request) use cases."""

from datetime import UTC, datetime

import pytest

from frontdesk.application.entitlements import (
    FeatureCatalog,
    RecordDemoLead,
    RequestFeature,
    ReviewFeatureRequest,
)
from frontdesk.domain.entitlements import Entitlement, FeatureRegistry, PremiumFeature
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, FeatureKey
from frontdesk.infrastructure.memory import (
    InMemoryDemoLeadRepository,
    InMemoryEntitlementRepository,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 3, 9, 0, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")
BIZ = BusinessId("biz")


def _registry() -> FeatureRegistry:
    return FeatureRegistry([PremiumFeature(VOICE, "Voice", "Answers calls.", "$1 per call")])


async def test_catalog_shows_no_status_before_a_request() -> None:
    catalog = FeatureCatalog(_registry(), InMemoryEntitlementRepository())

    views = await catalog.for_business(BIZ)

    assert [(v.key, v.name, v.pricing, v.status) for v in views] == [
        (VOICE, "Voice", "$1 per call", None)
    ]


async def test_catalog_reflects_an_active_entitlement() -> None:
    repo = InMemoryEntitlementRepository([Entitlement.requested(BIZ, VOICE, NOW).approve(NOW)])
    catalog = FeatureCatalog(_registry(), repo)

    (view,) = await catalog.for_business(BIZ)

    assert view.status is EntitlementStatus.ACTIVE


async def test_request_creates_a_pending_entitlement() -> None:
    repo = InMemoryEntitlementRepository()
    result = await RequestFeature(_registry(), repo, FixedClock(NOW)).execute(BIZ, VOICE)

    assert result.status is EntitlementStatus.REQUESTED
    assert result.requested_at == NOW
    assert await repo.get(BIZ, VOICE) == result  # persisted


async def test_request_is_idempotent_for_active_and_pending() -> None:
    active = Entitlement.requested(BIZ, VOICE, NOW).approve(NOW)
    repo = InMemoryEntitlementRepository([active])

    result = await RequestFeature(_registry(), repo, FixedClock(LATER)).execute(BIZ, VOICE)

    assert result == active  # an active feature is not downgraded, timestamps untouched


async def test_request_reopens_a_suspended_feature() -> None:
    suspended = Entitlement.requested(BIZ, VOICE, NOW).approve(NOW).suspend(NOW)
    repo = InMemoryEntitlementRepository([suspended])

    result = await RequestFeature(_registry(), repo, FixedClock(LATER)).execute(BIZ, VOICE)

    assert result.status is EntitlementStatus.REQUESTED
    assert result.requested_at == LATER  # a fresh request


async def test_request_rejects_an_unregistered_feature() -> None:
    with pytest.raises(UnknownFeature):
        await RequestFeature(_registry(), InMemoryEntitlementRepository(), FixedClock(NOW)).execute(
            BIZ, FeatureKey("ghost")
        )


async def test_approve_activates_a_pending_request() -> None:
    repo = InMemoryEntitlementRepository([Entitlement.requested(BIZ, VOICE, NOW)])

    result = await ReviewFeatureRequest(_registry(), repo, FixedClock(LATER)).approve(BIZ, VOICE)

    assert result.status is EntitlementStatus.ACTIVE
    assert result.decided_at == LATER
    assert await repo.active_features(BIZ) == frozenset({VOICE})


async def test_approve_without_a_prior_request_grants_directly() -> None:
    repo = InMemoryEntitlementRepository()

    result = await ReviewFeatureRequest(_registry(), repo, FixedClock(NOW)).approve(BIZ, VOICE)

    assert result.status is EntitlementStatus.ACTIVE  # operator can grant proactively
    assert await repo.get(BIZ, VOICE) == result


async def test_suspend_turns_an_active_feature_off() -> None:
    repo = InMemoryEntitlementRepository([Entitlement.requested(BIZ, VOICE, NOW).approve(NOW)])

    result = await ReviewFeatureRequest(_registry(), repo, FixedClock(LATER)).suspend(BIZ, VOICE)

    assert result.status is EntitlementStatus.SUSPENDED
    assert await repo.active_features(BIZ) == frozenset()


async def test_review_rejects_an_unregistered_feature() -> None:
    with pytest.raises(UnknownFeature):
        await ReviewFeatureRequest(
            _registry(), InMemoryEntitlementRepository(), FixedClock(NOW)
        ).approve(BIZ, FeatureKey("ghost"))


async def test_record_demo_lead_stores_the_email_and_feature() -> None:
    leads = InMemoryDemoLeadRepository()

    await RecordDemoLead(leads, SequentialIdGenerator("lead"), FixedClock(NOW)).execute(
        "caller@example.com", VOICE
    )

    assert [(lead.email, lead.feature_key, lead.created_at) for lead in leads.leads] == [
        ("caller@example.com", VOICE, NOW)
    ]
