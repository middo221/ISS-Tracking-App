from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from pydantic_settings import SettingsConfigDict

from iss_tracker.config import Settings
from iss_tracker.main import create_app
from iss_tracker.models.iss import Tle
from iss_tracker.services.tle_client import parse_tle

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TLE_URL = "https://celestrak.test/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle"


class IsolatedSettings(Settings):
    """Settings that ignore any local .env, so the suite behaves the same everywhere."""

    model_config = SettingsConfigDict(env_file=None)


@pytest.fixture
def tle_text() -> str:
    return (FIXTURES_DIR / "iss_tle.txt").read_text(encoding="utf-8")


@pytest.fixture
def tle(tle_text: str) -> Tle:
    return parse_tle(tle_text, default_name="ISS (ZARYA)")


@pytest.fixture
def settings() -> Settings:
    # Explicit values beat both the environment and any local .env file.
    return IsolatedSettings(
        tle_url=TLE_URL,
        tle_cache_ttl_seconds=7_200,
        tle_hard_expiry_seconds=259_200,
        tle_stale_warning_seconds=86_400,
        tle_fetch_timeout_seconds=5.0,
        cors_origins="http://localhost:5173",
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
