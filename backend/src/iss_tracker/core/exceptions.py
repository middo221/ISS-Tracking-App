class IssTrackerError(Exception):
    code = "internal_error"
    status_code = 500
    default_detail = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class TleUnavailableError(IssTrackerError):
    code = "tle_unavailable"
    status_code = 503
    default_detail = "Upstream TLE source unavailable"


class TleParseError(TleUnavailableError):
    code = "tle_invalid"
    default_detail = "Upstream TLE source returned unusable data"


class PropagationError(IssTrackerError):
    code = "propagation_failed"
    status_code = 500
    default_detail = "Could not propagate the orbit for the requested time"
