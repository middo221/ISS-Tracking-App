import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CacheEntry[T]:
    value: T
    age_seconds: float


class SingleFlightTtlCache[T]:
    """Holds one value, refreshed on demand once it passes `ttl_seconds`.

    Two behaviours matter beyond plain caching: concurrent misses collapse into a single
    upstream call, and a refresh failure keeps serving the previous value until it passes
    `hard_expiry_seconds`.
    """

    def __init__(
        self,
        ttl_seconds: float,
        hard_expiry_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if hard_expiry_seconds < ttl_seconds:
            raise ValueError("hard_expiry_seconds must be at least ttl_seconds")
        self._ttl = ttl_seconds
        self._hard_expiry = hard_expiry_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._stored: tuple[T, float] | None = None

    @property
    def age_seconds(self) -> float | None:
        if self._stored is None:
            return None
        return self._clock() - self._stored[1]

    def _entry_younger_than(self, max_age: float) -> CacheEntry[T] | None:
        if self._stored is None:
            return None
        value, stored_at = self._stored
        age = self._clock() - stored_at
        if age >= max_age:
            return None
        return CacheEntry(value, age)

    async def get(self, loader: Callable[[], Awaitable[T]]) -> CacheEntry[T]:
        entry = self._entry_younger_than(self._ttl)
        if entry is not None:
            return entry

        # Single flight: the first caller to take the lock performs the fetch. Everyone
        # else blocks here and re-checks afterwards, finding the value the winner stored.
        async with self._lock:
            entry = self._entry_younger_than(self._ttl)
            if entry is not None:
                return entry

            try:
                value = await loader()
            except Exception as exc:
                stale = self._entry_younger_than(self._hard_expiry)
                if stale is None:
                    raise
                logger.warning(
                    "Refresh failed, serving cached value",
                    extra={"age_seconds": round(stale.age_seconds, 1), "error": str(exc)},
                )
                return stale

            self._stored = (value, self._clock())
            return CacheEntry(value, 0.0)

    def clear(self) -> None:
        self._stored = None
