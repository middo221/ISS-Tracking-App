import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from iss_tracker.api.dependencies import IssServiceDep, SettingsDep
from iss_tracker.core.exceptions import IssTrackerError
from iss_tracker.models.iss import ErrorResponse, Position, Track
from iss_tracker.services.iss_service import IssService

router = APIRouter(tags=["iss"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {503: {"model": ErrorResponse}}


@router.get("/position", response_model=Position, responses=_ERROR_RESPONSES)
async def read_position(service: IssServiceDep) -> Position:
    return await service.get_position()


@router.get("/track", response_model=Track, responses=_ERROR_RESPONSES)
async def read_track(
    service: IssServiceDep,
    minutes_behind: Annotated[int, Query(ge=0, le=180)] = 30,
    minutes_ahead: Annotated[int, Query(ge=0, le=360)] = 90,
    step_seconds: Annotated[int, Query(ge=5, le=300)] = 30,
) -> Track:
    return await service.get_track(
        minutes_behind=minutes_behind,
        minutes_ahead=minutes_ahead,
        step_seconds=step_seconds,
    )


async def _position_events(service: IssService, interval_seconds: float) -> AsyncIterator[str]:
    while True:
        try:
            position = await service.get_position()
        except IssTrackerError as exc:
            payload = json.dumps({"detail": exc.detail, "code": exc.code})
            yield f"event: error\ndata: {payload}\n\n"
        else:
            yield f"event: position\ndata: {position.model_dump_json()}\n\n"
        await asyncio.sleep(interval_seconds)


@router.get("/stream")
async def stream_position(service: IssServiceDep, settings: SettingsDep) -> StreamingResponse:
    return StreamingResponse(
        _position_events(service, settings.stream_interval_seconds),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Tell nginx not to buffer, otherwise events arrive in batches.
            "X-Accel-Buffering": "no",
        },
    )
