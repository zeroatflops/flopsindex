"""flopsindex SDK exception hierarchy.

All SDK errors descend from `FlopsError` so callers can catch one
thing if they don't care about the distinction.
"""


class FlopsError(Exception):
    """Base SDK error. Carries (status_code, detail) when raised from
    an HTTP response."""

    def __init__(self, message: str, status_code: int = 0, detail=None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class FlopsAuthError(FlopsError):
    """401 / 403 — bad or missing API key, or scope insufficient."""


class FlopsNotFoundError(FlopsError):
    """404 — index_id / slug doesn't exist or is not on the public
    surface."""


class FlopsRateLimitError(FlopsError):
    """429 — rate limit exceeded. `retry_after_seconds` populated
    when the response carries the standard header."""

    def __init__(self, message: str, retry_after_seconds: int = 60,
                 status_code: int = 429, detail=None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message, status_code, detail)


class FlopsServerError(FlopsError):
    """5xx — server-side fault. Usually transient; retry with backoff."""
