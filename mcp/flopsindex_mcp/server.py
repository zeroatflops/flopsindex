"""FLOPS public MCP server — published on PyPI as flopsindex-mcp.

Tools (all work without a key): list_indices, get_index, verify,
get_price, search_indices. Set FLOPS_API_KEY for real-time precision.

flops://index/<INDEX_ID> returns the same payload as get_index.
"""
from __future__ import annotations

import json
import os
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
server: Server = Server("flopsindex")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_indices",
            description=(
                "List all public FLOPS compute-price indices. "
                "Returns a JSON array of {index_id, family, cadence, unit}. "
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
            description=(
                "Fetch the current published value for a FLOPS compute "
                "price index. Returns {value, unit, as_of, data_tier, "
                "confidence, verify_url, citation_url}. "
                "Source-opaque by design."
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
    raw = await _get_json(f"/v1/price/{iid}")
    body = json.dumps(_project_public_payload(raw, iid), indent=2)
    return [ReadResourceContents(content=body, mime_type="application/json")]


async def _tool_get_index(args: dict[str, Any]) -> str:
    """Resolve an index to the source-opaque public payload."""
    index_id = (args.get("index_id") or "").strip()
    if not index_id:
        return json.dumps({"error": "index_id is required"})
    raw = await _get_json(f"/v1/price/{index_id}")
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
            params["value"] = float(raw)
        except (TypeError, ValueError):
            return json.dumps({"ok": False, "reason": "bad_arg",
                               "detail": "value must be a number, e.g. 2.14"})

    data = await _defensive_get("/v1/verify", params=params)
    return json.dumps(data, indent=2)


async def _tool_get_price(args: dict[str, Any]) -> str:
    slug = (args.get("slug") or "").strip()
    if not slug:
        return json.dumps({"error": "slug is required"})
    data = await _get_json(f"/v1/price/{slug}")
    return json.dumps(data, indent=2)


async def _tool_search_indices(args: dict[str, Any]) -> str:
    q = (args.get("q") or "").strip()
    if not q:
        return json.dumps({"error": "q is required"})
    limit = int(args.get("limit") or 10)
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
