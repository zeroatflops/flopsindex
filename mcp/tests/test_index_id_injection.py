"""An LLM-supplied index id must never reshape the request path.

Every index id this server receives is chosen by a model, so it is untrusted
input: a prompt-injected model can pass any string it likes. Before the fix,
the id was interpolated raw into ``/v1/price/{id}``, so:

  * ``../v1/admin/orgs``  left /v1/price/ entirely -> /v1/v1/admin/orgs
  * ``X?full=1``          bolted a query string onto the request

and because ``_auth_headers()`` is unconditional, the operator's
``FLOPS_API_KEY`` was attached to whichever path was reached -- pulling an
authenticated response back into the model's context.

These tests assert on **the request that actually leaves the process**, driven
through the real ``call_tool`` / ``read_resource`` entry points rather than the
private helpers, so deleting a call to ``_price_path`` fails them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flopsindex_mcp import __version__  # noqa: E402
from flopsindex_mcp import server as srv  # noqa: E402

# Strings a prompt-injected model could plausibly emit. Each one, before the
# fix, either escaped /v1/price/ or altered the query.
#
# Note what is deliberately NOT here: "FLOPS-H100-OD " (trailing space). The
# handlers .strip() before validating, so that normalises to a real id and
# SHOULD be fetched. Listing it would have pinned a bug as a requirement.
HOSTILE_IDS = [
    "../v1/admin/orgs",
    "../../v1/methodology/internals",
    "..%2Fv1%2Fadmin%2Forgs",
    "FLOPS-H100-OD?full=1&internal=true",
    "FLOPS-H100-OD/../../v1/admin/orgs",
    "FLOPS-H100-OD#frag",
    "//evil.example.com/steal",
    "FLOPS H100",
    "",
]

_RAW_PRICE = {
    "index_id": "FLOPS-H100-OD",
    "value": 2.95,
    "unit": "USD/GPU-hr",
    "as_of": "2026-07-31T00:00:00+00:00",
    "data_tier": "LIVE",
    "confidence": "HIGH",
}


class _Recorder:
    """httpx.AsyncClient stand-in that records every request it is asked to
    make, whatever the URL. Answers 200 for anything so a leak shows up as a
    RECORDED REQUEST, never as an exception that could be mistaken for a
    refusal."""

    def __init__(self, sink: list[dict[str, Any]], **kw):
        self._sink = sink
        self._headers = kw.get("headers") or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def get(self, url, params=None):
        self._sink.append({"url": url, "params": params or {},
                           "headers": dict(self._headers)})
        return _Resp()


class _Resp:
    status_code = 200

    def json(self):
        return _RAW_PRICE

    def raise_for_status(self):
        return None


@pytest.fixture()
def sent(monkeypatch):
    """Records outbound requests; also arms an API key so any off-route
    request proves key replay, not just an unwanted fetch."""
    sink: list[dict[str, Any]] = []
    monkeypatch.setattr(srv, "FLOPS_API_KEY", "TEST-KEY-MUST-NOT-LEAK")
    monkeypatch.setattr(srv.httpx, "AsyncClient",
                        lambda **kw: _Recorder(sink, **kw))
    return sink


def _text(result) -> str:
    return "".join(c.text for c in result)


# ---------------------------------------------------------------------------
# The tools, driven through the real dispatch.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("bad", HOSTILE_IDS)
@pytest.mark.parametrize("tool,arg", [("get_price", "slug"),
                                      ("get_index", "index_id")])
async def test_hostile_id_makes_no_request_at_all(sent, tool, arg, bad):
    out = json.loads(_text(await srv.call_tool(tool, {arg: bad})))

    assert sent == [], (
        f"{tool} sent a request for {bad!r}: {sent}. A malformed index id "
        f"must be rejected BEFORE any I/O -- no path, no key, no timing signal."
    )
    assert "error" in out, f"{tool} accepted {bad!r} silently: {out}"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", HOSTILE_IDS)
async def test_hostile_resource_uri_makes_no_request_at_all(sent, bad):
    contents = list(await srv.read_resource(f"flops://index/{bad}"))

    assert sent == [], f"read_resource fetched for {bad!r}: {sent}"
    body = json.loads(contents[0].content)
    assert body.get("ok") is False


@pytest.mark.asyncio
async def test_valid_id_still_reaches_exactly_the_price_path(sent):
    """The guard must not break the happy path -- and the URL is pinned
    exactly, so a future 'fix' that re-opens the path fails here."""
    out = json.loads(_text(await srv.call_tool(
        "get_price", {"slug": "FLOPS-H100-OD"})))

    assert len(sent) == 1
    assert sent[0]["url"] == f"{srv.BASE_URL}/v1/price/FLOPS-H100-OD"
    assert out["value"] == 2.95


@pytest.mark.asyncio
async def test_key_only_ever_rides_the_price_path(sent):
    """Whatever the caller asks for, any request that DOES go out must be a
    /v1/price/ request -- that is the only route the key is allowed on."""
    for bad in HOSTILE_IDS:
        await srv.call_tool("get_price", {"slug": bad})
        await srv.call_tool("get_index", {"index_id": bad})
        await srv.read_resource(f"flops://index/{bad}")
    await srv.call_tool("get_price", {"slug": "FLOPS-H100-OD"})

    prefix = f"{srv.BASE_URL}/v1/price/"
    # Without this, the loop below is a no-op on an empty list and the whole
    # test degrades to a silent pass.
    assert len(sent) == 1, f"expected exactly the one legitimate call, got {sent}"
    for req in sent:
        assert req["url"].startswith(prefix), f"off-route request: {req}"
        assert req["url"] == prefix + "FLOPS-H100-OD"
        # the key is present on the legitimate call -- that is the point:
        # it is exactly what must never reach any other path.
        assert req["headers"].get("X-FLOPS-Api-Key") == "TEST-KEY-MUST-NOT-LEAK"


# ---------------------------------------------------------------------------
# The builder itself.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", HOSTILE_IDS)
def test_price_path_rejects(bad):
    assert srv._price_path(bad) is None


@pytest.mark.parametrize("good", ["FLOPS-H100-OD", "FLOPS-RTX6000Ada-OD",
                                  "FLOPS-A100-DEPIN", "a.b_c-1"])
def test_price_path_accepts_real_ids(good):
    assert srv._price_path(good) == f"/v1/price/{good}"


def test_price_path_percent_encodes_as_well_as_rejects(monkeypatch):
    """Second layer: if the pattern is ever loosened, quote(safe="") must
    still stop a slash from changing the path shape."""
    monkeypatch.setattr(srv, "_INDEX_ID_RE", __import__("re").compile(r"\A.*\Z"))
    assert srv._price_path("../admin") == "/v1/price/..%2Fadmin"
    assert srv._price_path("X?full=1") == "/v1/price/X%3Ffull%3D1"


# ---------------------------------------------------------------------------
# Version identity.
# ---------------------------------------------------------------------------
def test_server_reports_its_own_version_not_the_sdk_version():
    """Server("flopsindex") with no version= makes every MCP host display the
    `mcp` library version instead of ours, so a user cannot tell a fixed
    install from a broken one."""
    opts = srv.server.create_initialization_options()
    assert opts.server_version == __version__, (
        f"server advertises {opts.server_version!r}, expected {__version__!r}"
    )


# ---------------------------------------------------------------------------
# Argument bounds. inputSchema is enforced by the MCP HOST, so a caller that
# embeds this module directly is not covered by it -- these must hold in code.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", [
    (10 ** 30, 50), (-99999, 1), (0, 10), (None, 10),
    ("not-a-number", 10), (1e308, 50), (7, 7), (50, 50), (51, 50),
])
async def test_search_limit_is_bounded_in_code(sent, raw, expected):
    await srv.call_tool("search_indices", {"q": "H100", "limit": raw})

    assert len(sent) == 1
    assert sent[0]["params"]["limit"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["1e400", "Infinity", "-Infinity", "nan", "NaN"])
async def test_verify_refuses_non_finite_values(sent, bad):
    out = json.loads(_text(await srv.call_tool(
        "verify", {"index_id": "FLOPS-H100-OD", "value": bad})))

    assert sent == [], f"a non-finite value reached the wire: {sent}"
    assert out.get("reason") == "bad_arg"


# ---------------------------------------------------------------------------
# Tool descriptions are public copy: every connecting LLM reads them and acts
# on them. Two were wrong and were rewritten -- get_price claimed a 7-field
# filtered payload it does not filter, list_indices advertised a `cadence`
# field that exists nowhere in the API. A review then proved BOTH rewrites
# could be reverted with the whole suite staying green. Pinned now.
# ---------------------------------------------------------------------------
async def _desc(name: str) -> str:
    """Reads the description off the REAL list_tools() output, so a rewrite
    that never reaches the wire cannot pass. get_event_loop() was used here
    first and made these tests order-dependent -- green alone, red after the
    async suite had run."""
    tools = await srv.list_tools()
    return next(t.description for t in tools if t.name == name)


@pytest.mark.asyncio
async def test_get_price_description_lists_the_whole_envelope():
    """The live envelope is 14 fields; the first rewrite listed 13, dropping
    `upgrade`. Under-listing is the same defect at smaller scale."""
    d = await _desc("get_price")
    for field in ("index_id", "value", "unit", "as_of", "delayed", "data_tier",
                  "confidence", "change_24h", "disclaimer", "methodology_url",
                  "verify_url", "citation_url", "permalink", "upgrade"):
        assert field in d, f"get_price description omits {field!r}"


@pytest.mark.asyncio
async def test_get_price_does_not_claim_a_filter_it_does_not_apply():
    """It returns the server envelope verbatim (pinned by test_server.py).
    Claiming 'source-opaque by design' implied a client-side filter that only
    get_index actually has."""
    d = await _desc("get_price")
    assert "source-opaque by design" not in d.lower()


@pytest.mark.asyncio
async def test_list_indices_description_matches_the_real_shape():
    d = await _desc("list_indices")
    assert "cadence" not in d, "there is no `cadence` field anywhere in the API"
    assert "JSON array" not in d, "list_indices returns an object, not an array"
    for field in ("count", "indices"):
        assert field in d
