import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from iss_tracker.api.router import api_router
from iss_tracker.config import Settings, get_settings
from iss_tracker.core.cache import SingleFlightTtlCache
from iss_tracker.core.exceptions import IssTrackerError
from iss_tracker.core.logging import configure_logging, request_id_var
from iss_tracker.models.iss import Tle
from iss_tracker.services.iss_service import IssService
from iss_tracker.services.tle_client import TleClient

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


def build_service(settings: Settings) -> IssService:
    return IssService(
        tle_client=TleClient(
            url=settings.tle_url,
            timeout_seconds=settings.tle_fetch_timeout_seconds,
            default_name=settings.satellite_name,
        ),
        cache=SingleFlightTtlCache[Tle](
            ttl_seconds=settings.tle_cache_ttl_seconds,
            hard_expiry_seconds=settings.tle_hard_expiry_seconds,
        ),
        stale_warning_seconds=settings.tle_stale_warning_seconds,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service: IssService = app.state.iss_service
    await service.warm()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="ISS Tracker",
        version="0.1.0",
        summary="Live position, ground track and visibility footprint for the ISS.",
        lifespan=lifespan,
    )
    # Built here rather than in the lifespan so tests can drive the app over
    # ASGITransport, which does not run lifespan events.
    app.state.settings = settings
    app.state.iss_service = build_service(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        return response

    @app.exception_handler(IssTrackerError)
    async def handle_domain_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, IssTrackerError)
        logger.warning("Domain error", extra={"code": exc.code, "detail": exc.detail})
        return _error_response(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RequestValidationError)
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"][1:]) or "request"
        return _error_response(422, f"{location}: {first['msg']}", "validation_error")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, StarletteHTTPException)
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _error_response(exc.status_code, detail, f"http_{exc.status_code}")

    app.include_router(api_router)
    return app


app = create_app()
