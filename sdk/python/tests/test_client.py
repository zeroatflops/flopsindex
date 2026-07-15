"""Tests for the flopsindex Python SDK.

Network-free: every HTTP call is monkeypatched. Tests pin the
exception mapping + URL construction + auth gating.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# Add SDK to path (test runs from repo root)
SDK_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SDK_DIR))

from flopsindex import Client  # noqa: E402
from flopsindex.exceptions import (  # noqa: E402
    FlopsAuthError,
    FlopsError,
    FlopsNotFoundError,
    FlopsRateLimitError,
    FlopsServerError,
)


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


def test_public_methods_work_without_api_key(monkeypatch):
    """price / search / list_indices / verify must all work without
    an API key — that's the whole point of the public surface."""
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    # Stub _get so we don't hit the network
    with mock.patch.object(c, "_get", return_value={"ok": True}) as m:
        c.price("FLOPS-H100-OD")
        c.search("h100")
        c.list_indices()
        c.catalog()  # alias for list_indices
        c.verify("FLOPS-H100-OD", 2.45)
        assert m.call_count == 5


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("FLOPSINDEX_API_KEY", "flops_test_key")
    c = Client()
    assert c._api_key == "flops_test_key"


def test_api_key_from_constructor_wins(monkeypatch):
    monkeypatch.setenv("FLOPSINDEX_API_KEY", "from_env")
    c = Client(api_key="from_arg")
    assert c._api_key == "from_arg"


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


def test_price_url(monkeypatch):
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        return _FakeResp(json.dumps({"ok": True}).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)
    c.price("FLOPS-H100-OD")
    assert captured["url"] == "https://app.flopsindex.com/v1/price/FLOPS-H100-OD"
    # No API key header (we didn't set one)
    assert "X-flops-api-key" not in captured["headers"]


def test_list_indices_url(monkeypatch):
    """list_indices hits the public catalog mirror."""
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return _FakeResp(json.dumps({"ok": True}).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)
    c.list_indices()
    assert captured["url"] == "https://app.flopsindex.com/v2/catalog/public"


def test_catalog_is_alias_for_list_indices():
    """catalog() is a backwards-compatible alias for list_indices()."""
    assert Client.catalog is Client.list_indices


def test_api_key_forwarded_on_public_path(monkeypatch):
    """When a key is configured it is forwarded as X-FLOPS-Api-Key on
    the public price path — the server upgrades delayed → real-time."""
    monkeypatch.setenv("FLOPSINDEX_API_KEY", "flops_xxx")
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        return _FakeResp(json.dumps({"ok": True}).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)
    c.price("FLOPS-H100-OD")
    # urllib lowercases header names in the .headers dict
    assert "X-flops-api-key" in captured["headers"] or \
           "X-Flops-Api-Key" in captured["headers"]


def test_api_key_forwarded_on_verify_handshake(monkeypatch):
    """verify_handshake also forwards the key for the delayed→real-time
    upgrade."""
    monkeypatch.setenv("FLOPSINDEX_API_KEY", "flops_xxx")
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        return _FakeResp(json.dumps({"verified": True}).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)
    c.verify_handshake("FLOPS-H100-OD", value=2.45)
    assert "X-flops-api-key" in captured["headers"] or \
           "X-Flops-Api-Key" in captured["headers"]


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status,exc_class", [
    (401, FlopsAuthError),
    (403, FlopsAuthError),
    (404, FlopsNotFoundError),
    (429, FlopsRateLimitError),
    (500, FlopsServerError),
    (502, FlopsServerError),
    (503, FlopsServerError),
])
def test_http_error_maps_to_exception(monkeypatch, status, exc_class):
    """Each HTTP status code maps to the right exception class."""
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, status, "err",
            {"Retry-After": "120"},
            _FakeReader(json.dumps({"detail": f"status {status}"}).encode("utf-8")),
        )
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(exc_class) as exc_info:
        c.price("FLOPS-H100-OD")
    assert exc_info.value.status_code == status

    if status == 429:
        assert exc_info.value.retry_after_seconds == 120


def test_network_error_raises_flops_error(monkeypatch):
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(FlopsError) as exc_info:
        c.price("FLOPS-H100-OD")
    assert "connection refused" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeReader:
    """urllib.error.HTTPError needs a file-like object as `fp`."""
    def __init__(self, body: bytes):
        self._body = body

    def read(self, *args):
        return self._body


class _FakeResp:
    """Minimal context-manager fake for urllib.request.urlopen()."""
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


# ---------------------------------------------------------------------------
# verify_handshake — defensive citation helper
# ---------------------------------------------------------------------------


def test_verify_handshake_happy_path_returns_canonical_record(monkeypatch):
    """2xx → return the JSON record as-is (the verify endpoint's success
    shape). Caller checks .get('verified') / .get('actual_value')."""
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return _FakeResp(json.dumps({
            "verified": True, "index_id": "FLOPS-H100-OD",
            "actual_value": 2.45, "delta_pct": 0.0,
            "source_url": "https://app.flopsindex.com/i/FLOPS-H100-OD",
        }).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    out = c.verify_handshake("FLOPS-H100-OD", value=2.45)
    assert out["verified"] is True
    assert out["actual_value"] == 2.45
    assert "value=2.45" in captured["url"]
    assert "index_id=FLOPS-H100-OD" in captured["url"]


def test_verify_handshake_omits_value_when_none(monkeypatch):
    """value=None → just ask 'what's the latest tick?' without committing."""
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return _FakeResp(json.dumps({"actual_value": 2.45}).encode("utf-8"))
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    c.verify_handshake("FLOPS-H100-OD")
    assert "value=" not in captured["url"]
    assert "index_id=FLOPS-H100-OD" in captured["url"]


def test_verify_handshake_500_returns_upstream_http_error(monkeypatch):
    """Upstream 500 → defensive envelope; verify_handshake must not raise."""
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 500, "boom", {},
            _FakeReader(json.dumps({"detail": "internal"}).encode("utf-8")),
        )
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    out = c.verify_handshake("FLOPS-H100-OD", value=2.45)
    assert out["ok"] is False
    assert out["reason"] == "upstream_http_error"
    assert out["upstream_status"] == 500


@pytest.mark.parametrize("status,expected_reason", [
    (401, "auth_required"),
    (403, "auth_required"),
    (404, "endpoint_pending"),
    (400, "client_error"),
    (502, "upstream_http_error"),
    (503, "upstream_http_error"),
])
def test_verify_handshake_maps_status_to_reason(monkeypatch, status, expected_reason):
    """Each HTTP status code maps to the right defensive reason — same
    shape as MCP's _defensive_get, so MCP and SDK callers get identical
    error envelopes."""
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, status, "err", {},
            _FakeReader(b'{"detail":"x"}'),
        )
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    out = c.verify_handshake("FLOPS-H100-OD", value=2.45)
    assert out["ok"] is False
    assert out["reason"] == expected_reason
    assert out["upstream_status"] == status


def test_verify_handshake_network_error_returns_envelope(monkeypatch):
    """URLError (DNS, connection refused, timeout) → defensive envelope,
    not a raised exception. The handshake must survive a network blip."""
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    out = c.verify_handshake("FLOPS-H100-OD", value=2.45)
    assert out["ok"] is False
    assert out["reason"] == "network_error"
    assert "connection refused" in out["detail"]


def test_verify_legacy_method_still_raises(monkeypatch):
    """Backward-compat: existing .verify(index_id, value) still raises on
    non-2xx. Anyone who wants the defensive envelope opts in via
    .verify_handshake() — no silent shape change for legacy callers."""
    import urllib.error
    monkeypatch.delenv("FLOPSINDEX_API_KEY", raising=False)
    c = Client()

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 500, "boom", {},
            _FakeReader(b'{"detail":"internal"}'),
        )
    monkeypatch.setattr("flopsindex.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(FlopsServerError):
        c.verify("FLOPS-H100-OD", value=2.45)
