from typing import Any

from fastapi import APIRouter

from iss_tracker.api.dependencies import IssServiceDep
from iss_tracker.core.exceptions import TleUnavailableError
from iss_tracker.models.iss import ErrorResponse, HealthStatus

router = APIRouter(tags=["health"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {503: {"model": ErrorResponse}}


@router.get("/health", response_model=HealthStatus, responses=_ERROR_RESPONSES)
async def read_health(service: IssServiceDep) -> HealthStatus:
    age_seconds = service.tle_age_seconds
    if age_seconds is None:
        raise TleUnavailableError("No element set has been loaded yet")
    return HealthStatus(status="ok", tle_age_seconds=round(age_seconds))
