"""Tests for the flopsindex_mcp server.

We exercise the tool implementations directly (not through stdio) so
the tests stay fast and offline. httpx is monkeypatched per-test.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# Make `flopsindex_mcp` importable from `mcp/` parent dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flopsindex_mcp import server as srv  # noqa: E402


class _MockAsyncClient:
    """Stand-in for httpx.AsyncClient with a tiny route table."""

    def __init__(self, routes, **_kw):
        self._routes = routes
        self.last_url = None
        self.last_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def get(self, url, params=None):
        self.last_url = url
        self.last_params = params or {}
        for prefix, payload in self._routes.items():
            if prefix in url:
                if callable(payload):
                    body = payload(url, params)
                else:
                    body = payload
                # Pre-built _MockResp payload — pass through so callers
                # can stake non-200 status codes (used by defensive-envelope
                # tests for /v1/verify 500, etc).
                if isinstance(body, _MockResp):
                    return body
                return _MockResp(200, body)
        return _MockResp(404, {"error": "no route"})


class _MockResp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body) if not isinstance(body, str) else body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "boom",
                request=types.SimpleNamespace(url=self._body),
                response=self,
            )


def _install_mock(monkeypatch, routes):
    def factory(**kw):
        return _MockAsyncClient(routes, **kw)
    monkeypatch.setattr(srv.httpx, "AsyncClient", factory)


# ---------------------------------------------------------------------
# Tool registration smoke test — the EXACT public tool surface
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_list_has_public_tools():
    tools = await srv.list_tools()
    names = {t.name for t in tools}
    assert names.issuperset({"list_indices", "verify", "get_price",
                              "get_index", "search_indices"})


@pytest.mark.asyncio
async def test_tool_list_full_surface_pinned():
    """Pin the EXACT public tool surface so an accidental add/drop is caught."""
    tools = await srv.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "list_indices", "get_index", "verify", "get_price", "search_indices",
    }
    assert len(tools) == 5


def test_user_agent_tracks_package_version():
    # UA is now DERIVED from __version__ (no manual pin to drift). This
    # guards against a future refactor that hardcodes the UA string again,
    # which is what produced the old 0.5.2-vs-0.6.0 skew.
    from flopsindex_mcp import __version__
    assert srv.USER_AGENT == f"flopsindex-mcp/{__version__}"


# ---------------------------------------------------------------------
# AST-walk wiring catcher — bidirectional registration check
# ---------------------------------------------------------------------


def _extract_wiring_sets():
    """Parse server.py and return (declared_tools, dispatched_tools,
    implemented_tools) sets — used by the bidirectional catcher."""
    import ast as _ast
    src = Path(srv.__file__).read_text(encoding="utf-8")
    tree = _ast.parse(src)

    declared: set[str] = set()
    dispatched: set[str] = set()
    implemented: set[str] = set()

    for node in _ast.walk(tree):
        # Tool(name="...") declarations
        if isinstance(node, _ast.Call):
            func = node.func
            is_tool = (
                (isinstance(func, _ast.Name) and func.id == "Tool")
                or (isinstance(func, _ast.Attribute) and func.attr == "Tool")
            )
            if is_tool:
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, _ast.Constant):
                        declared.add(kw.value.value)
        # `_tool_<name>` async function implementations
        if isinstance(node, _ast.AsyncFunctionDef) and node.name.startswith("_tool_"):
            implemented.add(node.name[len("_tool_"):])
        # `elif name == "..."` dispatch branches inside call_tool
        if isinstance(node, _ast.Compare):
            if (
                isinstance(node.left, _ast.Name)
                and node.left.id == "name"
                and len(node.ops) == 1
                and isinstance(node.ops[0], _ast.Eq)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], _ast.Constant)
            ):
                dispatched.add(node.comparators[0].value)

    return declared, dispatched, implemented


def test_wiring_catcher_declared_matches_dispatched():
    """Every Tool() in list_tools has a dispatch branch in call_tool."""
    declared, dispatched, _ = _extract_wiring_sets()
    missing_dispatch = declared - dispatched
    assert not missing_dispatch, (
        f"Tools declared but not dispatched: {sorted(missing_dispatch)} — "
        "add an `elif name == '<tool>':` branch in call_tool()."
    )


def test_wiring_catcher_dispatched_matches_declared():
    """Every dispatch branch in call_tool has a Tool() declaration."""
    declared, dispatched, _ = _extract_wiring_sets()
    missing_declared = dispatched - declared
    assert not missing_declared, (
        f"Tools dispatched but not declared: {sorted(missing_declared)} — "
        "add a Tool(name='<tool>', ...) entry in list_tools()."
    )


def test_wiring_catcher_declared_matches_implemented():
    """Every Tool() declaration has a matching _tool_<name> coroutine."""
    declared, _, implemented = _extract_wiring_sets()
    missing_impl = declared - implemented
    assert not missing_impl, (
        f"Tools declared but not implemented: {sorted(missing_impl)} — "
        "add an `async def _tool_<name>(args):` function."
    )


def test_wiring_catcher_implemented_matches_declared():
    """Every _tool_<name> coroutine has a matching Tool() declaration."""
    declared, _, implemented = _extract_wiring_sets()
    orphan_impl = implemented - declared
    assert not orphan_impl, (
        f"Implementations without a Tool() declaration: {sorted(orphan_impl)} — "
        "either declare the Tool or remove the dead _tool_<name> coroutine."
    )


# ---------------------------------------------------------------------
# verify — defensive envelope on upstream errors
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_returns_ok_envelope_on_upstream_500(monkeypatch):
    """Upstream 500 must return a structured envelope, not raise."""
    _install_mock(monkeypatch, {"/v1/verify":
                                 _MockResp(500, {"detail": "boom"})})
    out = await srv._tool_verify({"index_id": "FLOPS-H100-OD"})
    data = json.loads(out)
    assert data["ok"] is False
    assert data["reason"] == "upstream_http_error"
    assert data["upstream_status"] == 500


@pytest.mark.asyncio
async def test_verify_happy_path_when_upstream_recovers(monkeypatch):
    _install_mock(monkeypatch, {"/v1/verify": {
        "verified": True, "index_id": "FLOPS-H100-OD", "actual_value": 2.45,
        "delta_pct": 0.0, "source_url": "https://app.flopsindex.com/i/FLOPS-H100-OD",
    }})
    out = await srv._tool_verify({"index_id": "FLOPS-H100-OD"})
    data = json.loads(out)
    assert data["verified"] is True
    assert data["actual_value"] == 2.45


@pytest.mark.asyncio
async def test_verify_requires_index_id():
    out = await srv._tool_verify({})
    data = json.loads(out)
    assert data["reason"] == "missing_arg"


# ---------------------------------------------------------------------
# Public source-opaque payload — get_index tool + flops://index resource
# ---------------------------------------------------------------------

# The live /v1/price shape (ts/tier) plus extra upstream fields the whitelist
# projection must NOT copy through — the public payload is opaque by
# construction, so only the whitelisted keys may ever appear.
_RAW_PRICE = {
    "index_id": "FLOPS-H100-OD",
    "value": 2.95,
    "unit": "USD/GPU-hr",
    "ts": "2026-01-01T12:00:00+00:00",
    "tier": "LIVE",
    "confidence": "HIGH",
    "verify_url": "https://app.flopsindex.com/v1/verify?index_id=FLOPS-H100-OD",
    "citation_url": "https://app.flopsindex.com/i/FLOPS-H100-OD",
    # Non-public upstream extras — projection must drop anything unlisted.
    "internal_detail_a": ["one", "two", "three"],
    "internal_detail_b": 3,
    "internal_detail_c": {"detail": "redacted"},
}


def test_project_public_payload_exact_field_set():
    """Projection emits exactly the public payload field set."""
    out = srv._project_public_payload(_RAW_PRICE, "FLOPS-H100-OD")
    assert set(out.keys()) == set(srv.PUBLIC_PAYLOAD_FIELDS)


def test_project_public_payload_only_public_keys():
    """Nothing outside the public whitelist survives, even when upstream
    carries extra fields."""
    out = srv._project_public_payload(_RAW_PRICE, "FLOPS-H100-OD")
    assert set(out).issubset(set(srv.PUBLIC_PAYLOAD_FIELDS))


def test_project_public_payload_normalizes_and_fills():
    """ts->as_of, tier->data_tier, verify/permalink/citation URLs filled."""
    out = srv._project_public_payload(_RAW_PRICE, "FLOPS-H100-OD")
    assert out["index_id"] == "FLOPS-H100-OD"
    assert out["value"] == 2.95
    assert out["unit"] == "USD/GPU-hr"
    assert out["as_of"] == "2026-01-01T12:00:00+00:00"
    assert out["data_tier"] == "LIVE"
    assert out["confidence"] == "HIGH"
    assert out["verify_url"].endswith("index_id=FLOPS-H100-OD")
    assert out["permalink"].endswith("/i/FLOPS-H100-OD")
    assert out["citation_url"].endswith("/i/FLOPS-H100-OD")
    assert "methodology_url" not in out


@pytest.mark.asyncio
async def test_get_price_passes_through_server_payload(monkeypatch):
    """get_price returns the server response as-is — the REST server is the
    source-opacity authority, so the client does not re-shape it."""
    _install_mock(monkeypatch, {"/v1/price/FLOPS-H100-OD": _RAW_PRICE})
    out = await srv._tool_get_price({"slug": "FLOPS-H100-OD"})
    data = json.loads(out)
    assert data["value"] == 2.95
    assert data["unit"] == "USD/GPU-hr"


@pytest.mark.asyncio
async def test_get_index_tool_returns_public_payload(monkeypatch):
    _install_mock(monkeypatch, {"/v1/price/FLOPS-H100-OD": _RAW_PRICE})
    out = await srv._tool_get_index({"index_id": "FLOPS-H100-OD"})
    data = json.loads(out)
    assert set(data.keys()) == set(srv.PUBLIC_PAYLOAD_FIELDS)
    assert data["value"] == 2.95


@pytest.mark.asyncio
async def test_get_index_tool_requires_index_id():
    out = await srv._tool_get_index({})
    assert "index_id" in json.loads(out)["error"]


@pytest.mark.asyncio
async def test_read_resource_returns_public_payload(monkeypatch):
    """The flops://index/<id> resource resolves to a source-opaque payload."""
    _install_mock(monkeypatch, {"/v1/price/FLOPS-H100-OD": _RAW_PRICE})
    contents = await srv.read_resource("flops://index/FLOPS-H100-OD")
    items = list(contents)
    assert len(items) == 1
    assert items[0].mime_type == "application/json"
    data = json.loads(items[0].content)
    assert set(data.keys()) == set(srv.PUBLIC_PAYLOAD_FIELDS)


@pytest.mark.asyncio
async def test_list_resources_builds_flops_uris(monkeypatch):
    _install_mock(monkeypatch, {"/v2/catalog/public": {"indices": [
        {"index_id": "FLOPS-H100-OD", "unit": "USD/GPU-hr"},
        {"index_id": "FLOPS-A100-SPOT", "unit": "USD/GPU-hr"},
        {"unit": "USD/GPU-hr"},  # malformed (no id) — must be skipped
    ]}})
    resources = await srv.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "flops://index/FLOPS-H100-OD" in uris
    assert "flops://index/FLOPS-A100-SPOT" in uris
    assert len(resources) == 2  # malformed entry skipped


def test_index_id_from_uri_round_trips():
    assert srv._index_id_from_uri("flops://index/FLOPS-H100-OD") == "FLOPS-H100-OD"
    assert srv._index_id_from_uri("flops://index/XXXX-FOO-BAR") == "XXXX-FOO-BAR"


def test_public_payload_contract_constants_are_complete():
    """Locks the published public payload field set."""
    assert srv.PUBLIC_PAYLOAD_FIELDS == (
        "index_id", "value", "unit", "as_of", "data_tier", "confidence",
        "verify_url", "citation_url", "permalink",
    )


# ---------------------------------------------------------------------
# FLOPS_API_KEY forwarded as X-FLOPS-Api-Key

def _capturing_factory(captured):
    """httpx.AsyncClient factory that records the headers kwarg."""
    class _Cap(_MockAsyncClient):
        def __init__(self, routes, **kw):
            super().__init__(routes, **kw)
            captured["headers"] = kw.get("headers", {})
    return lambda **kw: _Cap({"/v1/price": {"value": 1.0, "unit": "USD/GPU-hr"}}, **kw)


@pytest.mark.asyncio
async def test_keyed_client_forwards_api_key_header(monkeypatch):
    """FLOPS_API_KEY set → every request carries X-FLOPS-Api-Key."""
    monkeypatch.setattr(srv, "FLOPS_API_KEY", "test-key-123")
    captured: dict = {}
    monkeypatch.setattr(srv.httpx, "AsyncClient", _capturing_factory(captured))
    await srv._get_json("/v1/price/FLOPS-H100-OD")
    assert captured["headers"].get("X-FLOPS-Api-Key") == "test-key-123"


@pytest.mark.asyncio
async def test_keyless_client_sends_no_api_key_header(monkeypatch):
    """No FLOPS_API_KEY → no X-FLOPS-Api-Key header (genuine anon; the 5 public
    tools still work)."""
    monkeypatch.setattr(srv, "FLOPS_API_KEY", "")
    captured: dict = {}
    monkeypatch.setattr(srv.httpx, "AsyncClient", _capturing_factory(captured))
    await srv._get_json("/v1/price/FLOPS-H100-OD")
    assert "X-FLOPS-Api-Key" not in captured["headers"]


@pytest.mark.asyncio
async def test_defensive_get_also_forwards_api_key(monkeypatch):
    """_defensive_get must forward the API key header too."""
    monkeypatch.setattr(srv, "FLOPS_API_KEY", "k-456")
    captured: dict = {}
    monkeypatch.setattr(srv.httpx, "AsyncClient", _capturing_factory(captured))
    await srv._defensive_get("/v1/price/FLOPS-H100-OD")
    assert captured["headers"].get("X-FLOPS-Api-Key") == "k-456"


# ---------------------------------------------------------------------------
# CATCHER — the verify tool must FORWARD the caller's value.
# ---------------------------------------------------------------------------
# It previously called /v1/verify with only {"index_id": ...}, so it could only
# ever return verified:null — a lookup dressed up as a verification. The MCP
# server was the ONLY client that could not prove a citation, which is the whole
# point of the agentic surface. The mock below COMPUTES the receipt from the
# submitted value, so a server that forwards nothing fails these rather than
# passing against a mock that ignores its params.

import json as _json

import pytest as _pytest

from flopsindex_mcp import server as _srv


class _CapturingClient:
    def __init__(self):
        self.params = None

    async def _fake(self, path, params=None, **kw):
        self.params = params
        sub = (params or {}).get("value")
        published = 2.14
        if sub is None:
            return {"index_id": "FLOPS-H100-SPOT", "actual_value": published,
                    "verified": None, "delta_pct": None}
        verified = abs(float(sub) - published) <= 0.005
        return {
            "index_id": "FLOPS-H100-SPOT", "actual_value": published,
            "verified": verified, "expected": float(sub),
            "submitted_value": float(sub),
            "delta_pct": (float(sub) - published) / published * 100.0,
        }


@_pytest.fixture()
def cap(monkeypatch):
    c = _CapturingClient()
    monkeypatch.setattr(_srv, "_defensive_get", c._fake)
    return c


@_pytest.mark.asyncio
async def test_verify_forwards_value_on_the_wire(cap):
    await _srv._tool_verify({"index_id": "FLOPS-H100-SPOT", "value": 2.14})
    assert cap.params.get("value") == 2.14, (
        "the verify tool did not forward `value` — it can only return "
        "verified:null, which is the bug this catcher exists for"
    )


@_pytest.mark.asyncio
async def test_verify_true_on_correct_value(cap):
    out = _json.loads(await _srv._tool_verify(
        {"index_id": "FLOPS-H100-SPOT", "value": 2.14}))
    assert out["verified"] is True and out["delta_pct"] == 0.0


@_pytest.mark.asyncio
async def test_verify_false_on_wrong_value(cap):
    out = _json.loads(await _srv._tool_verify(
        {"index_id": "FLOPS-H100-SPOT", "value": 9.99}))
    assert out["verified"] is False
    assert out["delta_pct"] is not None


@_pytest.mark.asyncio
async def test_verify_without_value_stays_a_lookup(cap):
    out = _json.loads(await _srv._tool_verify({"index_id": "FLOPS-H100-SPOT"}))
    assert "value" not in (cap.params or {})
    assert out["verified"] is None, "absent must never read as a pass"


@_pytest.mark.asyncio
async def test_verify_forwards_zero(cap):
    """value=0 is falsy — a truthiness check would silently drop it."""
    await _srv._tool_verify({"index_id": "FLOPS-H100-SPOT", "value": 0})
    assert cap.params.get("value") == 0.0


@_pytest.mark.asyncio
async def test_verify_coerces_numeric_string(cap):
    out = _json.loads(await _srv._tool_verify(
        {"index_id": "FLOPS-H100-SPOT", "value": "2.14"}))
    assert out["verified"] is True, "LLMs stringify numbers routinely"


@_pytest.mark.asyncio
@_pytest.mark.parametrize("bad", ["cheap", "$2.14", True])
async def test_verify_rejects_garbage_without_calling_upstream(cap, bad):
    """Reject over guess: a wrong parse yields a confident WRONG receipt."""
    out = _json.loads(await _srv._tool_verify(
        {"index_id": "FLOPS-H100-SPOT", "value": bad}))
    assert out["ok"] is False and out["reason"] == "bad_arg"
    assert cap.params is None, "must not hit upstream on a bad arg"


def test_verify_schema_declares_optional_numeric_value():
    import asyncio
    tools = asyncio.run(_srv.list_tools())
    v = next(t for t in tools if t.name == "verify")
    props = v.inputSchema["properties"]
    assert props["value"]["type"] == "number"
    assert v.inputSchema["required"] == ["index_id"], "value must stay optional"
