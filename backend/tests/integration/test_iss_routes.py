import asyncio
import re

import httpx
import pytest
import respx
from fastapi import FastAPI

from tests.conftest import TLE_URL

ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def mock_celestrak(tle_text: str) -> respx.Route:
    return respx.get(TLE_URL).mock(return_value=httpx.Response(200, text=tle_text))


@respx.mock
async def test_position_returns_the_documented_payload(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    mock_celestrak(tle_text)

    response = await client.get("/api/v1/iss/position")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "timestamp",
        "latitude",
        "longitude",
        "altitude_km",
        "velocity_kmh",
        "footprint_radius_km",
        "tle_epoch",
    }
    assert -90 <= body["latitude"] <= 90
    assert -180 <= body["longitude"] <= 180
    assert 300 < body["altitude_km"] < 600
    assert 26_000 < body["velocity_kmh"] < 29_000
    assert body["footprint_radius_km"] > 0


@respx.mock
async def test_timestamps_are_utc_with_a_z_suffix(client: httpx.AsyncClient, tle_text: str) -> None:
    mock_celestrak(tle_text)

    body = (await client.get("/api/v1/iss/position")).json()

    assert ISO_Z.match(body["timestamp"])
    assert ISO_Z.match(body["tle_epoch"])


@respx.mock
async def test_track_returns_the_expected_number_of_points(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    mock_celestrak(tle_text)

    response = await client.get("/api/v1/iss/track")

    assert response.status_code == 200
    body = response.json()
    assert body["step_seconds"] == 30
    assert len(body["points"]) == (30 + 90) * 60 // 30 + 1


@respx.mock
async def test_track_honours_the_query_parameters(client: httpx.AsyncClient, tle_text: str) -> None:
    mock_celestrak(tle_text)

    response = await client.get(
        "/api/v1/iss/track",
        params={"minutes_behind": 10, "minutes_ahead": 20, "step_seconds": 60},
    )

    body = response.json()
    assert body["step_seconds"] == 60
    assert len(body["points"]) == (10 + 20) * 60 // 60 + 1


@respx.mock
async def test_track_points_are_in_ascending_time_order(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    mock_celestrak(tle_text)

    points = (await client.get("/api/v1/iss/track")).json()["points"]

    timestamps = [point["timestamp"] for point in points]
    assert timestamps == sorted(timestamps)
    assert all(-180 <= point["longitude"] <= 180 for point in points)


@respx.mock
@pytest.mark.parametrize(
    "params",
    [
        {"minutes_behind": -1},
        {"minutes_behind": 181},
        {"minutes_ahead": 361},
        {"step_seconds": 4},
        {"step_seconds": 301},
        {"step_seconds": "thirty"},
    ],
)
async def test_track_rejects_out_of_range_parameters(
    client: httpx.AsyncClient, tle_text: str, params: dict[str, str | int]
) -> None:
    mock_celestrak(tle_text)

    response = await client.get("/api/v1/iss/track", params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@respx.mock
async def test_health_reports_the_age_of_the_cached_element_set(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    mock_celestrak(tle_text)
    await client.get("/api/v1/iss/position")

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["tle_age_seconds"] >= 0


@respx.mock
async def test_health_is_503_before_any_element_set_has_loaded(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "No element set has been loaded yet",
        "code": "tle_unavailable",
    }


@respx.mock
async def test_position_is_503_when_the_upstream_is_down_and_nothing_is_cached(
    client: httpx.AsyncClient,
) -> None:
    respx.get(TLE_URL).mock(return_value=httpx.Response(500))

    response = await client.get("/api/v1/iss/position")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "tle_unavailable"
    assert "500" in body["detail"]


@respx.mock
async def test_cached_element_set_survives_an_upstream_outage(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    route = mock_celestrak(tle_text)
    first = await client.get("/api/v1/iss/position")
    assert first.status_code == 200

    route.mock(side_effect=httpx.ConnectError("celestrak is down"))
    later = await client.get("/api/v1/iss/position")

    assert later.status_code == 200
    assert later.json()["tle_epoch"] == first.json()["tle_epoch"]


@respx.mock
async def test_concurrent_requests_fetch_the_tle_once(
    client: httpx.AsyncClient, tle_text: str
) -> None:
    route = mock_celestrak(tle_text)

    responses = await asyncio.gather(*(client.get("/api/v1/iss/position") for _ in range(10)))

    assert all(response.status_code == 200 for response in responses)
    assert route.call_count == 1


@respx.mock
async def test_unknown_paths_use_the_shared_error_shape(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/iss/nowhere")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "http_404"}


@respx.mock
async def test_responses_carry_a_request_id(client: httpx.AsyncClient, tle_text: str) -> None:
    mock_celestrak(tle_text)

    response = await client.get("/api/v1/iss/position", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"


async def test_openapi_schema_documents_the_routes(client: httpx.AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    assert set(schema["paths"]) >= {
        "/api/v1/health",
        "/api/v1/iss/position",
        "/api/v1/iss/track",
        "/api/v1/iss/stream",
    }


async def test_docs_page_renders(client: httpx.AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


@respx.mock
async def test_lifespan_warms_the_cache(app: FastAPI, tle_text: str) -> None:
    route = mock_celestrak(tle_text)

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.get("/api/v1/health")

    assert route.call_count == 1
    assert response.status_code == 200
