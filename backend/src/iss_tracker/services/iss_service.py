import logging
from datetime import UTC, datetime, timedelta

from iss_tracker.core.cache import SingleFlightTtlCache
from iss_tracker.core.exceptions import IssTrackerError
from iss_tracker.models.iss import Position, Tle, Track, TrackPoint
from iss_tracker.services.propagator import Propagator
from iss_tracker.services.tle_client import TleClient

logger = logging.getLogger(__name__)


class IssService:
    def __init__(
        self,
        tle_client: TleClient,
        cache: SingleFlightTtlCache[Tle],
        stale_warning_seconds: float,
    ) -> None:
        self._tle_client = tle_client
        self._cache = cache
        self._stale_warning_seconds = stale_warning_seconds
        self._propagator: Propagator | None = None

    @property
    def tle_age_seconds(self) -> float | None:
        return self._cache.age_seconds

    async def warm(self) -> None:
        try:
            await self._current_propagator()
        except IssTrackerError as exc:
            # A cold start with the upstream down still yields a running app; /health
            # reports 503 until a later request manages to load an element set.
            logger.warning("TLE warm-up failed", extra={"error": exc.detail, "code": exc.code})

    async def get_position(self, at: datetime | None = None) -> Position:
        moment = at if at is not None else datetime.now(UTC)
        propagator = await self._current_propagator()
        geodetic = propagator.position_at(moment)

        return Position(
            timestamp=moment,
            latitude=geodetic.latitude,
            longitude=geodetic.longitude,
            altitude_km=geodetic.altitude_km,
            velocity_kmh=geodetic.velocity_kmh,
            footprint_radius_km=geodetic.footprint_radius_km,
            tle_epoch=propagator.tle.epoch,
        )

    async def get_track(
        self,
        minutes_behind: int,
        minutes_ahead: int,
        step_seconds: int,
    ) -> Track:
        propagator = await self._current_propagator()
        generated_at = datetime.now(UTC)

        span_seconds = (minutes_behind + minutes_ahead) * 60
        moments = [
            generated_at + timedelta(seconds=offset - minutes_behind * 60)
            for offset in range(0, span_seconds + 1, step_seconds)
        ]
        subpoints = propagator.subpoints_at(moments)

        return Track(
            generated_at=generated_at,
            step_seconds=step_seconds,
            points=[
                TrackPoint(
                    timestamp=moment,
                    latitude=subpoint.latitude,
                    longitude=subpoint.longitude,
                )
                for moment, subpoint in zip(moments, subpoints, strict=True)
            ],
        )

    async def _current_propagator(self) -> Propagator:
        entry = await self._cache.get(self._tle_client.fetch)
        tle = entry.value

        epoch_age_seconds = (datetime.now(UTC) - tle.epoch).total_seconds()
        if epoch_age_seconds > self._stale_warning_seconds:
            logger.warning(
                "Propagating from an old element set; accuracy is degraded",
                extra={
                    "epoch_age_seconds": round(epoch_age_seconds),
                    "tle_epoch": tle.epoch.isoformat(),
                },
            )

        propagator = self._propagator
        if propagator is None or propagator.tle != tle:
            propagator = Propagator(tle)
            self._propagator = propagator
        return propagator
