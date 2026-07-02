"""Entitlement transitions and the premium-feature registry — pure domain rules."""

from datetime import UTC, datetime

import pytest

from frontdesk.domain.entitlements import (
    Entitlement,
    FeatureRegistry,
    PremiumFeature,
)
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, FeatureKey

REQUESTED_AT = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 7, 2, 10, 30, tzinfo=UTC)
VOICE = FeatureKey("voice_receptionist")


def test_requested_starts_pending_and_inactive() -> None:
    entitlement = Entitlement.requested(BusinessId("b1"), VOICE, REQUESTED_AT)

    assert entitlement.status is EntitlementStatus.REQUESTED
    assert entitlement.requested_at == REQUESTED_AT
    assert entitlement.decided_at is None
    assert entitlement.is_active is False


def test_approve_activates_and_stamps_the_decision_time() -> None:
    approved = Entitlement.requested(BusinessId("b1"), VOICE, REQUESTED_AT).approve(DECIDED_AT)

    assert approved.status is EntitlementStatus.ACTIVE
    assert approved.is_active is True
    assert approved.decided_at == DECIDED_AT
    assert approved.requested_at == REQUESTED_AT  # the original request time is preserved


def test_suspend_turns_it_off() -> None:
    suspended = (
        Entitlement.requested(BusinessId("b1"), VOICE, REQUESTED_AT)
        .approve(DECIDED_AT)
        .suspend(DECIDED_AT)
    )

    assert suspended.status is EntitlementStatus.SUSPENDED
    assert suspended.is_active is False


def test_a_suspended_feature_can_be_reactivated() -> None:
    reactivated = (
        Entitlement.requested(BusinessId("b1"), VOICE, REQUESTED_AT)
        .suspend(DECIDED_AT)
        .approve(DECIDED_AT)
    )

    assert reactivated.is_active is True


def test_registry_lists_gets_and_requires_features() -> None:
    voice = PremiumFeature(VOICE, "Voice receptionist", "Answers calls.", "$1 per call")
    registry = FeatureRegistry([voice])

    assert registry.all() == (voice,)
    assert registry.get(VOICE) is voice
    assert registry.get(FeatureKey("missing")) is None
    assert registry.require(VOICE) is voice


def test_registry_require_rejects_an_unregistered_key() -> None:
    registry = FeatureRegistry([])

    with pytest.raises(UnknownFeature) as caught:
        registry.require(FeatureKey("nope"))

    assert caught.value.key == "nope"
