"""Public read client for the FLOPS HTTP API.

Stdlib urllib only — no third-party deps. Keyless by default;
FLOPSINDEX_API_KEY (or api_key=) upgrades delayed → real-time.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from flopsindex.exceptions import (
    FlopsAuthError,
    FlopsError,
    FlopsNotFoundError,
    FlopsRateLimitError,
    FlopsServerError,
)

logger = logging.getLogger("flopsindex")

_DEFAULT_BASE_URL = "https://app.flopsindex.com"
_DEFAULT_TIMEOUT = 30
_USER_AGENT_TEMPLATE = "flopsindex/{version} (+https://app.flopsindex.com)"


class Client:
    """FLOPS public read client.

    ::

        from flopsindex import Client
        c = Client()
        c.price("FLOPS-H100-OD")

    Optional api_key (or FLOPSINDEX_API_KEY env var) for real-time data.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
        user_agent: Optional[str] = None,
    ):
        self._api_key = api_key or os.environ.get("FLOPSINDEX_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        from flopsindex import __version__ as _v
        self._user_agent = user_agent or _USER_AGENT_TEMPLATE.format(version=_v)

    def price(self, index_id: str) -> Dict[str, Any]:
        """Latest public price for one index (delayed if no API key).

        Returns index_id, value, unit, ts, tier, confidence, verify_url,
        citation_url. Raises FlopsNotFoundError for unknown slugs.
        """
        return self._get(f"/v1/price/{urllib.parse.quote(index_id, safe='')}")

    def search(self, q: str, limit: int = 10) -> Dict[str, Any]:
        """Free-text query → matching index slugs."""
        return self._get("/v1/search",
                         params={"q": q, "limit": str(limit)})

    def list_indices(self) -> Dict[str, Any]:
        """Full public catalog (GET /v2/catalog/public)."""
        return self._get("/v2/catalog/public")

    catalog = list_indices  # alias

    def verify(self, index_id: str, value: float) -> Dict[str, Any]:
        """Check value against latest tick. Raises on HTTP errors."""
        return self._get(
            "/v1/verify",
            params={"index_id": index_id, "value": str(value)})

    def verify_handshake(
        self,
        index_id: str,
        value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Like verify(), but returns {ok: false, reason, ...} instead of raising.

        Typical use: price() → verify_handshake() → cite. Same error shape
        as the MCP server's /v1/verify path. Omit value to fetch latest tick only.
        """
        params: Dict[str, str] = {"index_id": index_id}
        if value is not None:
            params["value"] = str(value)
        url = self._base_url + "/v1/verify?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        if self._api_key:
            headers["X-FLOPS-Api-Key"] = self._api_key
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                try:
                    return json.loads(body)
                except ValueError:
                    return {"ok": False, "reason": "invalid_json",
                            "upstream_status": resp.status, "url": url}
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (401, 403):
                return {"ok": False, "reason": "auth_required",
                        "upstream_status": code, "url": url}
            if code == 404:
                return {"ok": False, "reason": "endpoint_pending",
                        "upstream_status": code, "url": url}
            if code >= 500:
                return {"ok": False, "reason": "upstream_http_error",
                        "upstream_status": code, "url": url}
            return {"ok": False, "reason": "client_error",
                    "upstream_status": code, "url": url}
        except urllib.error.URLError as exc:
            return {"ok": False, "reason": "network_error",
                    "url": url, "detail": str(exc.reason)[:300]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "network_error",
                    "url": url, "detail": str(exc)[:300]}

    def _get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = self._base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        if self._api_key:
            headers["X-FLOPS-Api-Key"] = self._api_key

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            self._raise_for_status(e.code, e.read().decode("utf-8", "replace"),
                                   e.headers)
        except urllib.error.URLError as e:
            raise FlopsError(f"network error: {e.reason}")
        raise FlopsError(f"unexpected: {path}")

    def _raise_for_status(
        self, status_code: int, body: str, headers,
    ) -> None:
        try:
            detail = json.loads(body)
        except Exception:
            detail = body
        msg = f"HTTP {status_code}"
        if isinstance(detail, dict) and "detail" in detail:
            msg += f": {detail['detail']}"
        if status_code in (401, 403):
            raise FlopsAuthError(msg, status_code=status_code, detail=detail)
        if status_code == 404:
            raise FlopsNotFoundError(msg, status_code=status_code, detail=detail)
        if status_code == 429:
            retry_after = 60
            try:
                retry_after = int(headers.get("Retry-After", "60"))
            except (ValueError, TypeError, AttributeError):
                pass
            raise FlopsRateLimitError(msg, retry_after_seconds=retry_after,
                                      status_code=status_code, detail=detail)
        if 500 <= status_code < 600:
            raise FlopsServerError(msg, status_code=status_code, detail=detail)
        raise FlopsError(msg, status_code=status_code, detail=detail)
