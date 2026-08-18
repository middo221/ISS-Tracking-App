from datetime import UTC, datetime, timedelta

import httpx

from iss_tracker.core.exceptions import TleParseError, TleUnavailableError
from iss_tracker.models.iss import Tle

TLE_LINE_LENGTH = 69
_EPOCH_COLUMNS = slice(18, 32)
_CATALOG_COLUMNS = slice(2, 7)
# TLEs carry a two-digit year; the accepted pivot puts 57-99 in the 1900s.
_CENTURY_PIVOT = 57


def _checksum(line: str) -> int:
    total = 0
    for char in line[: TLE_LINE_LENGTH - 1]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
    return total % 10


def _validate_line(line: str, *, number: int) -> None:
    if len(line) != TLE_LINE_LENGTH:
        raise TleParseError(
            f"TLE line {number} has {len(line)} characters, expected {TLE_LINE_LENGTH}"
        )
    if not line.startswith(f"{number} "):
        raise TleParseError(f"TLE line {number} is not numbered {number}")

    stated = line[TLE_LINE_LENGTH - 1]
    if not stated.isdigit() or int(stated) != _checksum(line):
        raise TleParseError(f"TLE line {number} failed its checksum")


def _parse_epoch(line1: str) -> datetime:
    raw = line1[_EPOCH_COLUMNS]
    try:
        two_digit_year = int(raw[:2])
        day_of_year = float(raw[2:])
    except ValueError as exc:
        raise TleParseError(f"Could not read the TLE epoch from {raw!r}") from exc

    year = 1900 + two_digit_year if two_digit_year >= _CENTURY_PIVOT else 2000 + two_digit_year
    return datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=day_of_year - 1.0)


def parse_tle(text: str, *, default_name: str) -> Tle:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise TleParseError("TLE source returned an empty response")

    name = default_name
    if not lines[0].startswith("1 "):
        name = lines[0]
        lines = lines[1:]

    if len(lines) < 2:
        # CelesTrak answers an unknown catalog number with plain text and HTTP 200.
        preview = " ".join(lines)[:80] if lines else "<nothing>"
        raise TleParseError(f"TLE source returned no element set: {preview!r}")

    line1, line2 = lines[0], lines[1]
    _validate_line(line1, number=1)
    _validate_line(line2, number=2)
    if line1[_CATALOG_COLUMNS] != line2[_CATALOG_COLUMNS]:
        raise TleParseError("TLE lines refer to different satellites")

    return Tle(name=name, line1=line1, line2=line2, epoch=_parse_epoch(line1))


class TleClient:
    def __init__(self, url: str, timeout_seconds: float, default_name: str) -> None:
        self._url = url
        self._timeout = timeout_seconds
        self._default_name = default_name

    async def fetch(self) -> Tle:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.get(self._url)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TleUnavailableError(
                f"TLE source returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise TleUnavailableError(f"Could not reach the TLE source: {exc}") from exc

        return parse_tle(response.text, default_name=self._default_name)
