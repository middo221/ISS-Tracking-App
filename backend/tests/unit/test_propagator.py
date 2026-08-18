import math
from datetime import UTC, datetime, timedelta

import pytest
from sgp4.api import Satrec, jday

from iss_tracker.core.exceptions import PropagationError
from iss_tracker.models.iss import Tle
from iss_tracker.services.propagator import (
    EARTH_MEAN_RADIUS_KM,
    Propagator,
    footprint_radius_km,
)

MOMENT = datetime(2026, 8, 17, 13, 0, 0, tzinfo=UTC)
ISS_INCLINATION_DEG = 51.6334

WGS84_SEMI_MAJOR_KM = 6378.137
WGS84_FLATTENING = 1 / 298.257223563


def _gmst_radians(julian_date_ut1: float) -> float:
    """Greenwich mean sidereal time, Vallado eq. 3-47."""
    centuries = (julian_date_ut1 - 2451545.0) / 36525.0
    seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * centuries
        + 0.093104 * centuries**2
        - 6.2e-6 * centuries**3
    )
    return math.radians((seconds % 86400.0) / 240.0)


def _ecef_to_geodetic(x: float, y: float, z: float) -> tuple[float, float, float]:
    eccentricity_sq = WGS84_FLATTENING * (2 - WGS84_FLATTENING)
    longitude = math.atan2(y, x)
    equatorial = math.hypot(x, y)

    latitude = math.atan2(z, equatorial * (1 - eccentricity_sq))
    altitude = 0.0
    for _ in range(12):
        curvature = WGS84_SEMI_MAJOR_KM / math.sqrt(1 - eccentricity_sq * math.sin(latitude) ** 2)
        altitude = equatorial / math.cos(latitude) - curvature
        latitude = math.atan2(
            z, equatorial * (1 - eccentricity_sq * curvature / (curvature + altitude))
        )

    return math.degrees(latitude), math.degrees(longitude), altitude


def reference_subpoint(tle: Tle, moment: datetime) -> tuple[float, float, float]:
    """Subpoint computed without Skyfield: raw SGP4, then a TEME->ECEF spin by GMST.

    This exists so the coordinate conversion in `propagator.py` is checked against
    something other than the library it is built on.
    """
    satellite = Satrec.twoline2rv(tle.line1, tle.line2)
    julian_day, fraction = jday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second + moment.microsecond / 1e6,
    )
    error, position_teme, _ = satellite.sgp4(julian_day, fraction)
    assert error == 0

    theta = _gmst_radians(julian_day + fraction)
    x, y, z = position_teme
    return _ecef_to_geodetic(
        x * math.cos(theta) + y * math.sin(theta),
        -x * math.sin(theta) + y * math.cos(theta),
        z,
    )


def test_position_matches_pinned_values(tle: Tle) -> None:
    position = Propagator(tle).position_at(MOMENT)

    # Pinned from the fixture TLE at a fixed instant, cross-checked below against an
    # independent SGP4 + TEME->ECEF conversion.
    assert position.latitude == pytest.approx(30.326910, abs=1e-3)
    assert position.longitude == pytest.approx(-137.068082, abs=1e-3)
    assert position.altitude_km == pytest.approx(414.9598, abs=1e-2)
    assert position.velocity_kmh == pytest.approx(27608.31, abs=1.0)
    assert position.footprint_radius_km == pytest.approx(2239.537, abs=1e-2)


def test_position_agrees_with_an_independent_conversion(tle: Tle) -> None:
    position = Propagator(tle).position_at(MOMENT)
    latitude, longitude, altitude = reference_subpoint(tle, MOMENT)

    # The residual is polar motion and the UT1/GAST corrections Skyfield applies and the
    # reference does not: fractions of a degree, versus the hundreds a frame error costs.
    assert position.latitude == pytest.approx(latitude, abs=0.05)
    assert position.longitude == pytest.approx(longitude, abs=0.05)
    assert position.altitude_km == pytest.approx(altitude, abs=1.0)


def test_position_is_physically_plausible(tle: Tle) -> None:
    position = Propagator(tle).position_at(MOMENT)

    assert 380.0 < position.altitude_km < 460.0
    assert 27_000.0 < position.velocity_kmh < 28_200.0
    assert abs(position.latitude) <= ISS_INCLINATION_DEG + 0.5
    assert -180.0 <= position.longitude <= 180.0


def test_returns_close_to_the_same_latitude_one_orbit_later(tle: Tle) -> None:
    propagator = Propagator(tle)
    orbital_period = timedelta(minutes=24 * 60 / 15.49472682)

    start = propagator.position_at(MOMENT)
    later = propagator.position_at(MOMENT + orbital_period)

    assert later.latitude == pytest.approx(start.latitude, abs=0.5)


def test_subpoints_are_returned_one_per_moment(tle: Tle) -> None:
    moments = [MOMENT + timedelta(seconds=30 * i) for i in range(10)]

    subpoints = Propagator(tle).subpoints_at(moments)

    assert len(subpoints) == len(moments)
    assert all(-180.0 <= point.longitude <= 180.0 for point in subpoints)
    assert all(abs(point.latitude) <= 90.0 for point in subpoints)


def test_subpoints_match_single_position_lookups(tle: Tle) -> None:
    propagator = Propagator(tle)
    moments = [MOMENT, MOMENT + timedelta(minutes=7)]

    subpoints = propagator.subpoints_at(moments)

    for moment, subpoint in zip(moments, subpoints, strict=True):
        single = propagator.position_at(moment)
        assert subpoint.latitude == pytest.approx(single.latitude, abs=1e-9)
        assert subpoint.longitude == pytest.approx(single.longitude, abs=1e-9)


def test_naive_datetimes_are_rejected(tle: Tle) -> None:
    with pytest.raises(PropagationError, match="timezone-aware"):
        Propagator(tle).position_at(datetime(2026, 8, 17, 13, 0, 0))


def test_empty_moment_list_is_rejected(tle: Tle) -> None:
    with pytest.raises(PropagationError, match="No times"):
        Propagator(tle).subpoints_at([])


def test_footprint_radius_is_zero_at_the_surface() -> None:
    assert footprint_radius_km(0.0) == 0.0


def test_footprint_radius_follows_the_horizon_formula() -> None:
    radius = EARTH_MEAN_RADIUS_KM
    expected = radius * math.acos(radius / (radius + 420.0))

    assert footprint_radius_km(420.0) == pytest.approx(expected)


def test_footprint_radius_grows_with_altitude() -> None:
    assert footprint_radius_km(400.0) < footprint_radius_km(500.0)
