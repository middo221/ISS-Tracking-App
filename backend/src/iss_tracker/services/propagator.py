import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

from iss_tracker.core.exceptions import PropagationError
from iss_tracker.models.iss import Tle

EARTH_MEAN_RADIUS_KM = 6371.0
_SECONDS_PER_HOUR = 3600.0

type FloatArray = np.ndarray[Any, np.dtype[np.float64]]

_timescale: Any = None


def get_timescale() -> Any:
    # Skyfield ships the leap-second and delta-T tables it needs, so this never
    # touches the network. Building one is slow enough to be worth sharing.
    global _timescale
    if _timescale is None:
        _timescale = load.timescale()
    return _timescale


def footprint_radius_km(altitude_km: float) -> float:
    """Great-circle radius of the region that can see the satellite above the horizon."""
    if altitude_km <= 0.0:
        return 0.0
    ratio = EARTH_MEAN_RADIUS_KM / (EARTH_MEAN_RADIUS_KM + altitude_km)
    return EARTH_MEAN_RADIUS_KM * math.acos(ratio)


@dataclass(frozen=True, slots=True)
class GeodeticPosition:
    latitude: float
    longitude: float
    altitude_km: float
    velocity_kmh: float
    footprint_radius_km: float


@dataclass(frozen=True, slots=True)
class Subpoint:
    latitude: float
    longitude: float


class Propagator:
    def __init__(self, tle: Tle) -> None:
        self._tle = tle
        self._timescale = get_timescale()
        self._satellite = EarthSatellite(tle.line1, tle.line2, tle.name, self._timescale)

    @property
    def tle(self) -> Tle:
        return self._tle

    def position_at(self, moment: datetime) -> GeodeticPosition:
        latitudes, longitudes, altitudes, speeds = self._propagate([moment])
        altitude_km = float(altitudes[0])
        return GeodeticPosition(
            latitude=float(latitudes[0]),
            longitude=float(longitudes[0]),
            altitude_km=altitude_km,
            velocity_kmh=float(speeds[0]) * _SECONDS_PER_HOUR,
            footprint_radius_km=footprint_radius_km(altitude_km),
        )

    def subpoints_at(self, moments: Sequence[datetime]) -> list[Subpoint]:
        latitudes, longitudes, _, _ = self._propagate(moments)
        return [
            Subpoint(latitude=float(lat), longitude=float(lon))
            for lat, lon in zip(latitudes, longitudes, strict=True)
        ]

    def _propagate(
        self, moments: Sequence[datetime]
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        if not moments:
            raise PropagationError("No times were supplied to propagate")
        if any(moment.tzinfo is None for moment in moments):
            raise PropagationError("Propagation requires timezone-aware datetimes")

        # Skyfield propagates a whole array of times in one pass, which is what makes a
        # 241-point ground track cheap enough to build per request.
        times = self._timescale.from_datetimes(list(moments))
        geocentric = self._satellite.at(times)
        geographic = wgs84.geographic_position_of(geocentric)

        latitudes = np.atleast_1d(np.asarray(geographic.latitude.degrees, dtype=float))
        longitudes = np.atleast_1d(np.asarray(geographic.longitude.degrees, dtype=float))
        altitudes = np.atleast_1d(np.asarray(geographic.elevation.km, dtype=float))

        # The reported speed is the magnitude of the geocentric velocity vector (~27,600 km/h),
        # not the speed of the subpoint across the ground.
        velocity = np.asarray(geocentric.velocity.km_per_s, dtype=float).reshape(3, -1)
        speeds = np.linalg.norm(velocity, axis=0)

        for values in (latitudes, longitudes, altitudes, speeds):
            if not np.all(np.isfinite(values)):
                raise PropagationError("SGP4 produced a non-finite result for the requested time")

        return latitudes, longitudes, altitudes, speeds
