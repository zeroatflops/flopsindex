"""FLOPS public MCP server — published on PyPI as flopsindex-mcp.

Tools (all work without a key): list_indices, get_index, verify,
get_price, search_indices. Set FLOPS_API_KEY for real-time precision.

flops://index/<INDEX_ID> returns the same payload as get_index.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
from typing import Any, Iterable

import httpx
from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from flopsindex_mcp import __version__

DEFAULT_BASE_URL = "https://app.flopsindex.com"
BASE_URL = os.environ.get("FLOPS_API_URL", DEFAULT_BASE_URL).rstrip("/")
HTTP_TIMEOUT_S = 15.0
USER_AGENT = f"flopsindex-mcp/{__version__}"

FLOPS_API_KEY = os.environ.get("FLOPS_API_KEY", "").strip()


def _auth_headers() -> dict[str, str]:
    """X-FLOPS-Api-Key header when FLOPS_API_KEY is set, else empty (anon)."""
    return {"X-FLOPS-Api-Key": FLOPS_API_KEY} if FLOPS_API_KEY else {}

# ---------------------------------------------------------------------------
# Public citation payload — whitelist-only field set for get_index / resources.
# ---------------------------------------------------------------------------
RESOURCE_URI_PREFIX = "flops://index/"
PUBLIC_PAYLOAD_FIELDS = (
    "index_id", "value", "unit", "as_of", "data_tier", "confidence",
    "verify_url", "citation_url", "permalink",
)
server: Server = Server("flopsindex", version=__version__)

# ---------------------------------------------------------------------------
# Index-id hygiene.
#
# Every index id reaching this server is chosen by an LLM, so it is untrusted
# input in the ordinary sense: a prompt-injected model can pass whatever
# string it likes. Interpolating that straight into the request path let a
# caller walk out of /v1/price/ ("../v1/admin/orgs" resolved to
# /v1/v1/admin/orgs) or bolt on a query string ("X?full=1") -- and because
# _auth_headers() is unconditional, the operator's FLOPS_API_KEY rode along to
# whatever path was reached. Not host-escaping (the base URL is fixed), but
# enough to pull an authenticated response back into the model's context.
#
# Two independent defences, because either alone is one typo from useless:
#   1. REJECT anything that is not a well-formed index id, before any I/O.
#   2. PERCENT-ENCODE with safe="" so a slash, dot-segment, "?" or "#" cannot
#      change the shape of the path even if the pattern is ever loosened.
# ---------------------------------------------------------------------------
_INDEX_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _price_path(index_id: str) -> str | None:
    """Return the /v1/price path for `index_id`, or None if it is malformed.

    None means "do not make the request" -- callers must not fall back to an
    unvalidated path.
    """
    if not _INDEX_ID_RE.match(index_id or ""):
        return None
    return "/v1/price/" + urllib.parse.quote(index_id, safe="")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_indices",
            description=(
                "List all public FLOPS compute-price indices. "
                # No `cadence` field exists anywhere in the API, and the
                # return is an OBJECT, not an array. A model told to expect
                # `cadence` reports it missing or invents it.
                "Returns {count, indices[]} where each row is "
                "{index_id, family, value, unit, as_of, confidence, "
                "change_24h, delayed}. "
                "Use this to discover available indices before calling "
                "get_index or verify. No auth required."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "family_filter": {
                        "type": "string",
                        "description": (
                            "Optional family prefix to filter by "
                            "(e.g. 'FLOPS-H100'). "
                            "Case-sensitive substring match."
                        ),
                    },
                },
            },
        ),
        Tool(
            name="verify",
            description=(
                "Check a FLOPS index value against the published index. Pass "
                "`value` with a number you are about to cite (or already hold) "
                "and the response tells you whether it is right: `verified` "
                "true/false, `expected` (what you submitted), `actual_value` "
                "(what FLOPS publishes) and `delta_pct`. Omit `value` to simply "
                "look up the current published value — then `verified` is null, "
                "which means 'not checked', NOT 'correct'. Note: without an API "
                "key you are checked against the public value, which is rounded "
                "to 2 decimals and delayed onto a 6-hour grid, so a "
                "full-precision real-time number will not match anonymously."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "index_id": {
                        "type": "string",
                        "description": (
                            "FLOPS index identifier "
                            "(e.g. 'FLOPS-H100-OD', 'FLOPS-A100-SPOT')."
                        ),
                    },
                    "value": {
                        "type": "number",
                        "description": (
                            "Optional. The number you want checked, e.g. 2.14. "
                            "Omit it to do a plain lookup."
                        ),
                    },
                },
                "required": ["index_id"],
            },
        ),
        Tool(
            name="get_price",
            # Describes the PASS-THROUGH honestly. This tool deliberately
            # returns the server envelope verbatim -- the REST API is the
            # source-opacity authority, and test_server.py pins that as the
            # contract. The old text listed 7 fields and promised
            # "source-opaque by design", implying a client-side filter that
            # does not exist; get_index is the filtered one.
            description=(
                "Fetch the current published value for a FLOPS compute "
                "price index. Returns the published envelope as-is: "
                "{index_id, value, unit, as_of, delayed, data_tier, "
                "confidence, change_24h, disclaimer, methodology_url, "
                "verify_url, citation_url, permalink, upgrade} -- the "
                "14-field envelope. Values are delayed "
                "and indicative. Use get_index for the reduced, "
                "citation-only payload."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": (
                            "FLOPS index slug, e.g. FLOPS-H100-OD or "
                            "FLOPS-A100-SPOT."
                        ),
                    },
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="get_index",
            description=(
                "Resolve a FLOPS index to its source-opaque PUBLIC payload "
                "(the public citation contract). Returns "
                "{index_id, value, unit, as_of, data_tier, confidence, "
                "verify_url, citation_url, permalink}. Prefer this when "
                "you intend to CITE the value. Also exposed as the MCP "
                "resource flops://index/<INDEX_ID>."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "index_id": {
                        "type": "string",
                        "description": (
                            "FLOPS index id / slug, e.g. 'FLOPS-H100-OD' "
                            "or 'FLOPS-A100-SPOT'."
                        ),
                    },
                },
                "required": ["index_id"],
            },
        ),
        Tool(
            name="search_indices",
            description=(
                "Resolve a free-text query to canonical FLOPS index slugs. "
                "Use when you don't know the exact slug — e.g. 'H100 spot' "
                "returns matching catalog entries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Free-text query (e.g. 'H100 on-demand').",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["q"],
            },
        ),
    ]


async def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT_S,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json",
                 **_auth_headers()},
    ) as c:
        r = await c.get(f"{BASE_URL}{path}", params=params)
        r.raise_for_status()
        return r.json()


async def _defensive_get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> Any:
    """Fetch JSON with a defensive ok:false envelope on failure."""
    full = f"{BASE_URL}{path}"
    merged_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        **_auth_headers(),
        **(headers or {}),
    }
    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_S,
            headers=merged_headers,
        ) as c:
            r = await c.get(full, params=params)
            code = r.status_code
            if 200 <= code < 300:
                try:
                    return r.json()
                except ValueError:
                    return {"ok": False, "reason": "invalid_json",
                            "upstream_status": code, "url": full}
            if code == 401 or code == 403:
                return {"ok": False, "reason": "auth_required",
                        "upstream_status": code, "url": full}
            if code == 404:
                return {"ok": False, "reason": "endpoint_pending",
                        "upstream_status": code, "url": full}
            if code >= 500:
                return {"ok": False, "reason": "upstream_http_error",
                        "upstream_status": code, "url": full}
            return {"ok": False, "reason": "client_error",
                    "upstream_status": code, "url": full,
                    "detail": r.text[:500]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "network_error",
                "url": full, "detail": str(exc)[:300]}


def _project_public_payload(raw: Any, index_id: str) -> dict[str, Any]:
    """Project any price/index payload down to the public field set."""
    src = raw if isinstance(raw, dict) else {}
    iid = (src.get("index_id") or index_id or "").strip()
    return {
        "index_id": iid,
        "value": src.get("value"),
        "unit": src.get("unit"),
        "as_of": src.get("as_of") or src.get("ts") or src.get("value_ts"),
        "data_tier": src.get("data_tier") or src.get("tier"),
        "confidence": src.get("confidence"),
        "verify_url": (
            src.get("verify_url") or f"{BASE_URL}/v1/verify?index_id={iid}"
        ),
        "citation_url": src.get("citation_url") or f"{BASE_URL}/i/{iid}",
        "permalink": src.get("permalink") or f"{BASE_URL}/i/{iid}",
    }


def _index_id_from_uri(uri: Any) -> str:
    """Extract the index_id from a flops://index/<INDEX_ID> resource URI."""
    s = str(uri)
    if RESOURCE_URI_PREFIX in s:
        return s.split(RESOURCE_URI_PREFIX, 1)[1].strip("/")
    return s.rstrip("/").rsplit("/", 1)[-1]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """Enumerate every public index appropriate for public resource."""
    data = await _get_json("/v2/catalog/public")
    indices = data.get("indices") if isinstance(data, dict) else data
    resources: list[Resource] = []
    for entry in indices or []:
        if not isinstance(entry, dict):
            continue
        iid = (entry.get("index_id") or "").strip()
        if not iid:
            continue
        unit = entry.get("unit")
        resources.append(Resource(
            uri=f"{RESOURCE_URI_PREFIX}{iid}",
            name=iid,
            title=f"{iid} — FLOPS reference value",
            description=(
                "Source-opaque public payload (value + verify/citation URLs)."
                + (f" Unit: {unit}." if unit else "")
            ),
            mimeType="application/json",
        ))
    return resources


@server.read_resource()
async def read_resource(uri: Any) -> Iterable[ReadResourceContents]:
    """Resolve a flops://index/<id> resource to its public payload."""
    iid = _index_id_from_uri(uri)
    if not iid:
        body = json.dumps({"ok": False, "reason": "bad_uri", "uri": str(uri)})
        return [ReadResourceContents(content=body, mime_type="application/json")]
    path = _price_path(iid)
    if path is None:
        body = json.dumps({"ok": False, "reason": "bad_index_id",
                           "uri": str(uri)})
        return [ReadResourceContents(content=body, mime_type="application/json")]
    raw = await _get_json(path)
    body = json.dumps(_project_public_payload(raw, iid), indent=2)
    return [ReadResourceContents(content=body, mime_type="application/json")]


async def _tool_get_index(args: dict[str, Any]) -> str:
    """Resolve an index to the source-opaque public payload."""
    index_id = (args.get("index_id") or "").strip()
    if not index_id:
        return json.dumps({"error": "index_id is required"})
    path = _price_path(index_id)
    if path is None:
        return json.dumps({
            "error": "invalid_index_id",
            "detail": ("index_id must look like FLOPS-H100-OD "
                       "(letters, digits, '.', '_', '-'). "
                       "Use search_indices or list_indices to resolve one."),
        })
    raw = await _get_json(path)
    return json.dumps(_project_public_payload(raw, index_id), indent=2)


async def _tool_list_indices(args: dict[str, Any]) -> str:
    family = (args.get("family_filter") or "").strip() or None
    data = await _get_json("/v2/catalog/public")
    indices = data.get("indices") if isinstance(data, dict) else data
    if not isinstance(indices, list):
        indices = []
    if family:
        indices = [i for i in indices if family in (i.get("index_id") or "")]
    return json.dumps({
        "count": len(indices),
        "family_filter": family,
        "indices": indices,
        "catalog_url": f"{BASE_URL}/v2/catalog/public",
    }, indent=2)


async def _tool_verify(args: dict[str, Any]) -> str:
    index_id = (args.get("index_id") or "").strip()
    if not index_id:
        return json.dumps({"ok": False, "reason": "missing_arg",
                           "detail": "index_id is required"})

    params: dict[str, Any] = {"index_id": index_id}

    # Forward the caller's number so the endpoint actually CHECKS it. Without
    # this the tool can only ever return verified:null — a lookup dressed up as
    # a verification.
    raw = args.get("value")
    if raw is not None and raw != "":
        # bool is an int subclass; True would otherwise coerce to 1.0 and get a
        # confident receipt for a value nobody submitted.
        if isinstance(raw, bool):
            return json.dumps({"ok": False, "reason": "bad_arg",
                               "detail": "value must be a number"})
        try:
            # LLMs routinely stringify numbers, so "2.14" is accepted. "$2.14"
            # is NOT guessed at: a wrong parse yields a confident, wrong
            # receipt, which is worse than refusing.
            parsed = float(raw)
            # inf/nan parse cleanly but cannot be a submitted price, and
            # would produce a confident verdict against a meaningless value
            # -- the same reason bool is refused above.
            if parsed != parsed or parsed in (float("inf"), float("-inf")):
                return json.dumps({"ok": False, "reason": "bad_arg",
                                   "detail": "value must be a finite number"})
            params["value"] = parsed
        except (TypeError, ValueError):
            return json.dumps({"ok": False, "reason": "bad_arg",
                               "detail": "value must be a number, e.g. 2.14"})

    data = await _defensive_get("/v1/verify", params=params)
    return json.dumps(data, indent=2)


async def _tool_get_price(args: dict[str, Any]) -> str:
    slug = (args.get("slug") or "").strip()
    if not slug:
        return json.dumps({"error": "slug is required"})
    path = _price_path(slug)
    if path is None:
        return json.dumps({
            "error": "invalid_slug",
            "detail": ("slug must look like FLOPS-H100-OD "
                       "(letters, digits, '.', '_', '-'). "
                       "Use search_indices or list_indices to resolve one."),
        })
    data = await _get_json(path)
    return json.dumps(data, indent=2)


async def _tool_search_indices(args: dict[str, Any]) -> str:
    q = (args.get("q") or "").strip()
    if not q:
        return json.dumps({"error": "q is required"})
    # Bounded here, not only by inputSchema: jsonschema is enforced by the
    # MCP host, so anything embedding this module directly bypasses it.
    # "or 10" also turns an explicit 0 into 10, which is the intent.
    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError, OverflowError):
        # OverflowError is float("inf") -> int; without it the blanket
        # handler returns a raw CPython message into the model's context.
        limit = 10
    limit = max(1, min(limit, 50))
    data = await _get_json("/v1/search", params={"q": q, "limit": limit})
    return json.dumps(data, indent=2)


@server.call_tool()
async def call_tool(name: str, args: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "list_indices":
            out = await _tool_list_indices(args)
        elif name == "verify":
            out = await _tool_verify(args)
        elif name == "get_price":
            out = await _tool_get_price(args)
        elif name == "get_index":
            out = await _tool_get_index(args)
        elif name == "search_indices":
            out = await _tool_search_indices(args)
        else:
            out = json.dumps({"error": f"unknown tool: {name}"})
    except httpx.HTTPStatusError as exc:
        out = json.dumps({
            "error": "upstream_http_error",
            "status": exc.response.status_code,
            "url": str(exc.request.url),
        })
    except Exception as exc:  # noqa: BLE001
        out = json.dumps({"error": "tool_failed", "detail": str(exc)})
    return [TextContent(type="text", text=out)]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
