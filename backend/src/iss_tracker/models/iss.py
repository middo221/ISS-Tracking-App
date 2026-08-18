from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _to_utc_z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# Every timestamp on the wire is UTC with a trailing `Z`; pydantic's default would
# emit `+00:00` instead.
UtcDatetime = Annotated[datetime, PlainSerializer(_to_utc_z, return_type=str, when_used="json")]


class Tle(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    line1: str
    line2: str
    epoch: UtcDatetime


class Position(BaseModel):
    timestamp: UtcDatetime = Field(description="Instant the position was computed for.")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_km: float = Field(description="Height above the WGS84 ellipsoid.")
    velocity_kmh: float = Field(description="Magnitude of the geocentric velocity vector.")
    footprint_radius_km: float = Field(
        description="Surface radius of the region from which the station is above the horizon."
    )
    tle_epoch: UtcDatetime = Field(description="Epoch of the element set used for propagation.")


class TrackPoint(BaseModel):
    timestamp: UtcDatetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Track(BaseModel):
    generated_at: UtcDatetime
    step_seconds: int
    points: list[TrackPoint] = Field(
        description=(
            "Chronological subpoints. Longitudes stay in [-180, 180]; the client splits the "
            "polyline at the antimeridian."
        )
    )


class HealthStatus(BaseModel):
    status: str
    tle_age_seconds: int = Field(description="Seconds since the cached element set was fetched.")


class ErrorResponse(BaseModel):
    detail: str
    code: str
