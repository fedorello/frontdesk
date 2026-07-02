"""Premium-feature access — the single gate every premium feature calls.

``FeatureAccess.is_enabled`` is what a feature (e.g. the voice receptionist, from the private layer)
checks before serving. It reads the business's active entitlements and validates the key against the
registry so an unregistered feature can never be silently allowed.
"""

import logging

from frontdesk.application.ports import EntitlementRepository
from frontdesk.domain.entitlements import FeatureRegistry
from frontdesk.domain.ids import BusinessId, FeatureKey

_logger = logging.getLogger("frontdesk.entitlements")


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
