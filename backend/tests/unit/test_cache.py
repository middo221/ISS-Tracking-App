import asyncio

import pytest

from iss_tracker.core.cache import SingleFlightTtlCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class CountingLoader:
    def __init__(self, value: str = "v1", delay: float = 0.0) -> None:
        self.value = value
        self.delay = delay
        self.calls = 0

    async def __call__(self) -> str:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.value


async def test_serves_cached_value_until_ttl_expires() -> None:
    clock = FakeClock()
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000, clock=clock)
    loader = CountingLoader()

    assert (await cache.get(loader)).value == "v1"
    clock.advance(99)
    entry = await cache.get(loader)

    assert loader.calls == 1
    assert entry.age_seconds == pytest.approx(99)


async def test_refreshes_once_ttl_has_passed() -> None:
    clock = FakeClock()
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000, clock=clock)
    loader = CountingLoader()

    await cache.get(loader)
    clock.advance(101)
    loader.value = "v2"

    assert (await cache.get(loader)).value == "v2"
    assert loader.calls == 2


async def test_concurrent_misses_trigger_a_single_upstream_fetch() -> None:
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000)
    loader = CountingLoader(delay=0.02)

    entries = await asyncio.gather(*(cache.get(loader) for _ in range(20)))

    assert loader.calls == 1
    assert {entry.value for entry in entries} == {"v1"}


async def test_serves_stale_value_when_refresh_fails() -> None:
    clock = FakeClock()
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000, clock=clock)

    await cache.get(CountingLoader())
    clock.advance(500)

    async def failing_loader() -> str:
        raise RuntimeError("upstream down")

    entry = await cache.get(failing_loader)

    assert entry.value == "v1"
    assert entry.age_seconds == pytest.approx(500)


async def test_raises_once_the_stale_value_passes_the_hard_ceiling() -> None:
    clock = FakeClock()
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000, clock=clock)

    await cache.get(CountingLoader())
    clock.advance(1_001)

    async def failing_loader() -> str:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError, match="upstream down"):
        await cache.get(failing_loader)


async def test_first_load_failure_propagates() -> None:
    cache = SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=1_000)

    async def failing_loader() -> str:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError):
        await cache.get(failing_loader)
    assert cache.age_seconds is None


def test_rejects_a_hard_expiry_below_the_ttl() -> None:
    with pytest.raises(ValueError, match="at least"):
        SingleFlightTtlCache[str](ttl_seconds=100, hard_expiry_seconds=10)
