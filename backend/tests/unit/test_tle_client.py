from datetime import UTC, datetime

import httpx
import pytest
import respx

from iss_tracker.core.exceptions import TleParseError, TleUnavailableError
from iss_tracker.services.tle_client import TleClient, parse_tle
from tests.conftest import TLE_URL

VALID_LINE_1 = "1 25544U 98067A   26229.53453565  .00005086  00000+0  98784-4 0  9995"
VALID_LINE_2 = "2 25544  51.6334 356.4696 0007520  56.7242 303.4466 15.49472682581269"


def make_client() -> TleClient:
    return TleClient(url=TLE_URL, timeout_seconds=5.0, default_name="ISS (ZARYA)")


def test_parses_a_three_line_element_set(tle_text: str) -> None:
    tle = parse_tle(tle_text, default_name="FALLBACK")

    assert tle.name == "ISS (ZARYA)"
    assert tle.line1 == VALID_LINE_1
    assert tle.line2 == VALID_LINE_2


def test_parses_a_two_line_element_set_using_the_default_name() -> None:
    tle = parse_tle(f"{VALID_LINE_1}\n{VALID_LINE_2}\n", default_name="FALLBACK")

    assert tle.name == "FALLBACK"


def test_parses_the_epoch_from_the_day_of_year(tle_text: str) -> None:
    tle = parse_tle(tle_text, default_name="ISS (ZARYA)")

    # 26229.53453565 -> day 229 of 2026 (17 August), 0.53453565 of a day.
    assert tle.epoch.year == 2026
    assert tle.epoch.timetuple().tm_yday == 229
    assert tle.epoch.tzinfo is UTC
    expected = datetime(2026, 8, 17, 12, 49, 43, 880160, tzinfo=UTC)
    assert abs((tle.epoch - expected).total_seconds()) < 1e-3


def test_two_digit_years_of_57_and_above_land_in_the_nineteen_hundreds() -> None:
    line1 = VALID_LINE_1[:18] + "99229.53453565" + VALID_LINE_1[32:]
    line1 = line1[:68] + str(_checksum_of(line1))

    assert parse_tle(f"{line1}\n{VALID_LINE_2}", default_name="X").epoch.year == 1999


def _checksum_of(line: str) -> int:
    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
    return total % 10


def test_tolerates_trailing_whitespace_and_blank_lines() -> None:
    text = f"ISS (ZARYA)      \n\n{VALID_LINE_1}  \n{VALID_LINE_2}\n\n"

    assert parse_tle(text, default_name="X").name == "ISS (ZARYA)"


def test_rejects_a_broken_checksum() -> None:
    broken = VALID_LINE_1[:68] + "0"

    with pytest.raises(TleParseError, match="checksum"):
        parse_tle(f"{broken}\n{VALID_LINE_2}", default_name="X")


def test_rejects_a_line_of_the_wrong_length() -> None:
    with pytest.raises(TleParseError, match="characters"):
        parse_tle(f"{VALID_LINE_1[:60]}\n{VALID_LINE_2}", default_name="X")


def test_rejects_lines_from_different_satellites() -> None:
    body = "2 43013  97.7000 100.0000 0001000  90.0000 270.0000 15.00000000 1000"
    other = body + str(_checksum_of(body))

    with pytest.raises(TleParseError, match="different satellites"):
        parse_tle(f"{VALID_LINE_1}\n{other}", default_name="X")


def test_rejects_an_empty_response() -> None:
    with pytest.raises(TleParseError, match="empty"):
        parse_tle("   \n\n", default_name="X")


def test_rejects_the_celestrak_no_data_message() -> None:
    with pytest.raises(TleParseError, match="no element set"):
        parse_tle("No GP data found\n", default_name="X")


@respx.mock
async def test_fetch_returns_a_parsed_tle(tle_text: str) -> None:
    route = respx.get(TLE_URL).mock(return_value=httpx.Response(200, text=tle_text))

    tle = await make_client().fetch()

    assert route.called
    assert tle.line1 == VALID_LINE_1


@respx.mock
async def test_fetch_raises_on_an_upstream_error_status() -> None:
    respx.get(TLE_URL).mock(return_value=httpx.Response(503))

    with pytest.raises(TleUnavailableError, match="HTTP 503"):
        await make_client().fetch()


@respx.mock
async def test_fetch_raises_when_the_upstream_is_unreachable() -> None:
    respx.get(TLE_URL).mock(side_effect=httpx.ConnectError("no route to host"))

    with pytest.raises(TleUnavailableError, match="Could not reach"):
        await make_client().fetch()


@respx.mock
async def test_fetch_raises_when_the_upstream_times_out() -> None:
    respx.get(TLE_URL).mock(side_effect=httpx.ReadTimeout("timed out"))

    with pytest.raises(TleUnavailableError):
        await make_client().fetch()
