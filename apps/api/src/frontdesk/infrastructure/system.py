"""Clock and id-generator adapters — a real one and a deterministic fake each."""

import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime


class SystemRandom:
    """The real source of randomness (non-crypto; fine for picking filler phrases)."""

    def __init__(self) -> None:
        self._rng = random.Random()

    def choice(self, items: Sequence[str]) -> str:
        return self._rng.choice(list(items))


class FixedRandom:
    """A deterministic Random for tests: always returns the first item."""

    def choice(self, items: Sequence[str]) -> str:
        return next(iter(items))


class SystemClock:
    """The real clock — UTC now."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock frozen at a chosen instant, for deterministic tests."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class UuidIdGenerator:
    """The real id generator — random UUIDs."""

    def new(self) -> str:
        return str(uuid.uuid4())


class SequentialIdGenerator:
    """A deterministic id generator: ``id-1``, ``id-2``, … for tests."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._count = 0

    def new(self) -> str:
        self._count += 1
        return f"{self._prefix}-{self._count}"
