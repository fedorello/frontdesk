"""The in-memory rate limiter: a fixed window per key that resets once it elapses."""

from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter


async def test_allows_up_to_limit_then_blocks() -> None:
    clock = {"t": 1000.0}
    limiter = InMemoryRateLimiter(now=lambda: clock["t"])

    first_three = [await limiter.hit("ip-1", 3, 60) for _ in range(3)]
    assert all(first_three)  # the first 3 are allowed
    assert await limiter.hit("ip-1", 3, 60) is False  # the 4th in the window is blocked
    assert await limiter.hit("ip-2", 3, 60) is True  # a different key is independent


async def test_window_resets_after_it_elapses() -> None:
    clock = {"t": 0.0}
    limiter = InMemoryRateLimiter(now=lambda: clock["t"])

    for _ in range(3):
        await limiter.hit("ip", 3, 60)
    assert await limiter.hit("ip", 3, 60) is False  # blocked within the window

    clock["t"] = 61.0  # the window has elapsed
    assert await limiter.hit("ip", 3, 60) is True  # a fresh window starts
