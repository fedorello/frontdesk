"""Premium features and per-business entitlements — the pure domain.

A ``PremiumFeature`` is a catalog entry (config-driven, held in a ``FeatureRegistry``). An
``Entitlement`` is one business's stake in one feature, moving through requested → active ↔
suspended. A business "has" a feature iff it holds an ACTIVE entitlement for it. See
docs/plans/premium-features-plan.md.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from frontdesk.domain.enums import EntitlementStatus
from frontdesk.domain.errors import UnknownFeature
from frontdesk.domain.ids import BusinessId, DemoLeadId, FeatureKey


@dataclass(frozen=True, slots=True)
class PremiumFeature:
    """A sellable feature the platform offers, shown in the catalog and the landing."""

    key: FeatureKey
    name: str
    description: str
    pricing: str  # display copy, e.g. "$1 per call"


@dataclass(frozen=True, slots=True)
class Entitlement:
    """One business's access to one premium feature, with an audit of when it was decided."""

    business_id: BusinessId
    feature_key: FeatureKey
    status: EntitlementStatus
    requested_at: datetime  # tz-aware UTC
    decided_at: datetime | None = None  # when an operator last approved/suspended it

    @classmethod
    def requested(
        cls, business_id: BusinessId, feature_key: FeatureKey, now: datetime
    ) -> Entitlement:
        """A fresh, owner-initiated request awaiting an operator's decision."""
        return cls(business_id, feature_key, EntitlementStatus.REQUESTED, now)

    @property
    def is_active(self) -> bool:
        return self.status is EntitlementStatus.ACTIVE

    def approve(self, now: datetime) -> Entitlement:
        """Grant the feature (idempotent), stamping when the decision was made."""
        return replace(self, status=EntitlementStatus.ACTIVE, decided_at=now)

    def suspend(self, now: datetime) -> Entitlement:
        """Turn the feature off — an operator's suspension or a rejected request (idempotent)."""
        return replace(self, status=EntitlementStatus.SUSPENDED, decided_at=now)


class FeatureRegistry:
    """The known premium features, keyed by their stable ``FeatureKey`` (built from config)."""

    def __init__(self, features: Sequence[PremiumFeature]) -> None:
        self._by_key: dict[FeatureKey, PremiumFeature] = {f.key: f for f in features}

    def all(self) -> tuple[PremiumFeature, ...]:
        return tuple(self._by_key.values())

    def get(self, key: FeatureKey) -> PremiumFeature | None:
        return self._by_key.get(key)

    def require(self, key: FeatureKey) -> PremiumFeature:
        """The feature for ``key``, or ``UnknownFeature`` if it is not registered."""
        feature = self._by_key.get(key)
        if feature is None:
            raise UnknownFeature(key)
        return feature


@dataclass(frozen=True, slots=True)
class DemoLead:
    """A visitor who signed in on the landing to try a feature's live demo — a captured lead."""

    id: DemoLeadId
    email: str
    feature_key: FeatureKey
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DemoNumber:
    """A landing-demo phone number for one language (revealed after a lead signs in)."""

    language: str
    e164: str
    label: str
