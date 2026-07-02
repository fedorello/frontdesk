"""Premium-feature access — the single gate every premium feature calls.

``FeatureAccess.is_enabled`` is what a feature (e.g. the voice receptionist, from the private layer)
checks before serving. It reads the business's active entitlements and validates the key against the
registry so an unregistered feature can never be silently allowed.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from frontdesk.application.ports import (
    Clock,
    DemoLeadRepository,
    EntitlementDirectory,
    EntitlementRepository,
    IdGenerator,
)
from frontdesk.domain.entitlements import DemoLead, Entitlement, FeatureRegistry
from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.ids import BusinessId, DemoLeadId, FeatureKey

_logger = logging.getLogger("frontdesk.entitlements")


@dataclass(frozen=True, slots=True)
class FeatureView:
    """A catalog entry joined with a business's own status — ``None`` means never requested."""

    key: FeatureKey
    name: str
    description: str
    pricing: str
    status: EntitlementStatus | None


class FeatureAccess:
    """Whether a business may use a premium feature. One gate reused by every feature."""

    def __init__(self, entitlements: EntitlementRepository, registry: FeatureRegistry) -> None:
        self._entitlements = entitlements
        self._registry = registry

    async def is_enabled(self, business_id: BusinessId, feature_key: FeatureKey) -> bool:
        """True iff ``business_id`` holds an ACTIVE entitlement for ``feature_key``.

        Raises ``UnknownFeature`` if the key is not registered (a config/routing bug, never a
        silent allow).
        """
        self._registry.require(feature_key)
        enabled = feature_key in await self._entitlements.active_features(business_id)
        _logger.info(
            "feature_access business=%s feature=%s enabled=%s", business_id, feature_key, enabled
        )
        return enabled


class FeatureCatalog:
    """The premium-feature catalog joined with one business's status — for the owner dashboard."""

    def __init__(self, registry: FeatureRegistry, directory: EntitlementDirectory) -> None:
        self._registry = registry
        self._directory = directory

    async def for_business(self, business_id: BusinessId) -> tuple[FeatureView, ...]:
        held = await self._directory.for_business(business_id)
        by_key = {item.feature_key: item for item in held}
        return tuple(
            FeatureView(
                feature.key,
                feature.name,
                feature.description,
                feature.pricing,
                by_key[feature.key].status if feature.key in by_key else None,
            )
            for feature in self._registry.all()
        )


class RequestFeature:
    """An owner asks to enable a premium feature — idempotent; an operator approves it later."""

    def __init__(
        self, registry: FeatureRegistry, entitlements: EntitlementRepository, clock: Clock
    ) -> None:
        self._registry = registry
        self._entitlements = entitlements
        self._clock = clock

    async def execute(self, business_id: BusinessId, feature_key: FeatureKey) -> Entitlement:
        """Record (or re-open) a request. A no-op if the feature is already active or pending.

        Raises ``UnknownFeature`` for an unregistered key.
        """
        self._registry.require(feature_key)
        existing = await self._entitlements.get(business_id, feature_key)
        if existing is not None and existing.status is not EntitlementStatus.SUSPENDED:
            return existing  # already active or already pending — nothing to do
        requested = Entitlement.requested(business_id, feature_key, self._clock.now())
        await self._entitlements.save(requested)
        _logger.info("feature_requested business=%s feature=%s", business_id, feature_key)
        return requested


class ReviewFeatureRequest:
    """An operator's decision on a premium feature — approve (activate) or suspend a business's."""

    def __init__(
        self, registry: FeatureRegistry, entitlements: EntitlementRepository, clock: Clock
    ) -> None:
        self._registry = registry
        self._entitlements = entitlements
        self._clock = clock

    async def approve(self, business_id: BusinessId, feature_key: FeatureKey) -> Entitlement:
        """Grant the feature (creating the record if the operator grants with no prior request)."""
        return await self._decide(business_id, feature_key, Entitlement.approve)

    async def suspend(self, business_id: BusinessId, feature_key: FeatureKey) -> Entitlement:
        """Turn the feature off for this business."""
        return await self._decide(business_id, feature_key, Entitlement.suspend)

    async def _decide(
        self,
        business_id: BusinessId,
        feature_key: FeatureKey,
        transition: Callable[[Entitlement, datetime], Entitlement],
    ) -> Entitlement:
        self._registry.require(feature_key)
        existing = await self._entitlements.get(business_id, feature_key)
        base = existing or Entitlement.requested(business_id, feature_key, self._clock.now())
        decided = transition(base, self._clock.now())
        await self._entitlements.save(decided)
        _logger.info(
            "feature_decision business=%s feature=%s status=%s",
            business_id,
            feature_key,
            decided.status.value,
        )
        return decided


class RecordDemoLead:
    """Stores a landing-demo lead — the email captured before revealing a feature's demo numbers."""

    def __init__(self, leads: DemoLeadRepository, ids: IdGenerator, clock: Clock) -> None:
        self._leads = leads
        self._ids = ids
        self._clock = clock

    async def execute(self, email: str, feature_key: FeatureKey) -> None:
        await self._leads.record(
            DemoLead(DemoLeadId(self._ids.new()), email, feature_key, self._clock.now())
        )
        _logger.info("demo_lead_recorded feature=%s", feature_key)  # email is PII → DEBUG only
        _logger.debug("demo_lead email=%s feature=%s", email, feature_key)
