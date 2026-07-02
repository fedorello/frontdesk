"""FeatureAccess gate + the in-memory entitlement fakes."""

from datetime import UTC, datetime

import pytest

from frontdesk.application.entitlements import FeatureAccess
from frontdesk.domain.entitlements import Entitlement, FeatureRegistry, PremiumFeature
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, FeatureKey
from frontdesk.infrastructure.memory import InMemoryEntitlementRepository

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")
BIZ = BusinessId("biz")
OTHER = BusinessId("other")


def _registry() -> FeatureRegistry:
    return FeatureRegistry([PremiumFeature(VOICE, "Voice", "Answers calls.", "$1 per call")])


def _access(*entitlements: Entitlement) -> FeatureAccess:
    return FeatureAccess(InMemoryEntitlementRepository(entitlements), _registry())


async def test_is_enabled_true_for_an_active_entitlement() -> None:
    access = _access(Entitlement.requested(BIZ, VOICE, NOW).approve(NOW))

    assert await access.is_enabled(BIZ, VOICE) is True


async def test_is_enabled_false_when_only_requested_or_suspended() -> None:
    requested = _access(Entitlement.requested(BIZ, VOICE, NOW))
    suspended = _access(Entitlement.requested(BIZ, VOICE, NOW).approve(NOW).suspend(NOW))

    assert await requested.is_enabled(BIZ, VOICE) is False
    assert await suspended.is_enabled(BIZ, VOICE) is False


async def test_is_enabled_false_for_a_business_without_the_entitlement() -> None:
    access = _access(Entitlement.requested(OTHER, VOICE, NOW).approve(NOW))

    assert await access.is_enabled(BIZ, VOICE) is False  # OTHER's grant does not leak to BIZ


async def test_is_enabled_rejects_an_unregistered_feature() -> None:
    with pytest.raises(UnknownFeature):
        await _access().is_enabled(BIZ, FeatureKey("ghost"))


async def test_repository_save_upserts_and_directory_views_filter() -> None:
    repo = InMemoryEntitlementRepository()
    await repo.save(Entitlement.requested(BIZ, VOICE, NOW))

    assert await repo.get(BIZ, VOICE) is not None
    assert (await repo.pending())[0].status is EntitlementStatus.REQUESTED
    assert await repo.active_features(BIZ) == frozenset()  # requested is not active

    await repo.save(Entitlement.requested(BIZ, VOICE, NOW).approve(NOW))  # upsert to active

    assert await repo.active_features(BIZ) == frozenset({VOICE})
    assert await repo.pending() == ()  # no longer pending
    assert len(await repo.for_business(BIZ)) == 1
