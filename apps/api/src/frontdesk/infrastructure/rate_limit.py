"""A per-process fixed-window rate limiter (the ``RateLimiter`` port).

Suitable for a single API instance — counters live in memory and aren't shared across
processes. Swap for a Redis-backed implementation (INCR + EXPIRE) when scaling horizontally;
the port stays the same.
"""

import time
from collections.abc import Callable

_CLEANUP_EVERY = 256  # opportunistically drop expired buckets to bound memory


class InMemoryRateLimiter:
    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._buckets: dict[str, tuple[float, int]] = {}  # key -> (window_expiry, count)
        self._ops = 0

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = self._now()
        self._ops += 1
        if self._ops % _CLEANUP_EVERY == 0:
            self._buckets = {k: v for k, v in self._buckets.items() if v[0] > now}
        expiry, count = self._buckets.get(key, (0.0, 0))
        if now >= expiry:  # window elapsed (or first hit) → start a fresh one
            expiry, count = now + window_seconds, 0
        count += 1
        self._buckets[key] = (expiry, count)
        return count <= limit
