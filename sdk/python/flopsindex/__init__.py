"""flopsindex — Python SDK for the FLOPS public API."""
from flopsindex.client import Client
from flopsindex.exceptions import (
    FlopsError,
    FlopsAuthError,
    FlopsNotFoundError,
    FlopsRateLimitError,
)

__version__ = "0.8.2"
__all__ = [
    "Client",
    "FlopsError",
    "FlopsAuthError",
    "FlopsNotFoundError",
    "FlopsRateLimitError",
    "__version__",
]
