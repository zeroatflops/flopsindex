"""Live proof: an MCP client resolves a real FLOPS price from app.flopsindex.com.

Spawns flopsindex-mcp over stdio, then via the standard MCP client:
  1. list_resources()                    -> finds flops://index/<id>
  2. read_resource(flops://index/<id>)   -> public payload
  3. call_tool("get_index", ...)         -> same payload via the tool

The public payload is a whitelist (server-side source-opaque authority), so
this proof asserts POSITIVELY that only the expected public keys are present —
it does not enumerate internal upstream field names. Exits non-zero if an
unexpected key appears or the value / verify URL is missing.

Run (from anywhere):
    python mcp/scripts/live_proof.py
    python mcp/scripts/live_proof.py FLOPS-A100-SPOT
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from pydantic import AnyUrl

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PKG_DIR = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("FLOPS_API_URL", "https://app.flopsindex.com")

# The public citation contract — the ONLY keys a public payload may carry.
# Asserting a subset of this is the positive form of source-opacity: anything
# outside the whitelist is unexpected, without ever naming an internal field.
ALLOWED_PUBLIC_KEYS = frozenset({
    "index_id", "value", "unit", "as_of", "data_tier", "confidence",
    "verify_url", "citation_url", "permalink",
})


def _unexpected_keys(obj) -> list[str]:
    """Top-level keys that are NOT part of the public citation contract."""
    if not isinstance(obj, dict):
        return []
    return sorted(k for k in obj if k not in ALLOWED_PUBLIC_KEYS)


async def main(index_id: str) -> int:
    env = {**os.environ, "FLOPS_API_URL": BASE_URL, "PYTHONPATH": str(PKG_DIR)}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from flopsindex_mcp.server import main; main()"],
        env=env,
        cwd=str(PKG_DIR),
    )
    print(f"# MCP live proof — server target {BASE_URL}, index {index_id}\n")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"[1] initialize -> server {init.serverInfo.name} "
                  f"v{init.serverInfo.version}")

            res = await session.list_resources()
            uri = f"flops://index/{index_id}"
            found = [r for r in res.resources if str(r.uri) == uri]
            print(f"[2] list_resources -> {len(res.resources)} resources; "
                  f"{uri} present: {bool(found)}")

            rr = await session.read_resource(AnyUrl(uri))
            block = rr.contents[0]
            payload = json.loads(block.text)
            print(f"[3] read_resource({uri}) [mimeType={block.mimeType}]:")
            print(json.dumps(payload, indent=2))

            tool = await session.call_tool("get_index", {"index_id": index_id})
            tool_payload = json.loads(tool.content[0].text)
            print(f"\n[4] call_tool get_index({index_id}):")
            print(json.dumps(tool_payload, indent=2))

            unexpected = sorted(
                set(_unexpected_keys(payload) + _unexpected_keys(tool_payload))
            )
            keys_ok = (
                set(payload).issubset(ALLOWED_PUBLIC_KEYS)
                and set(tool_payload).issubset(ALLOWED_PUBLIC_KEYS)
            )
            has_value = payload.get("value") is not None
            has_verify = bool(payload.get("verify_url"))
            print("\n# ---- verdict ----")
            print(f"  value resolved      : {payload.get('value')} "
                  f"{payload.get('unit')}  -> {has_value}")
            print(f"  verify_url present  : {has_verify}")
            print(f"  public keys only    : {keys_ok}")
            print(f"  unexpected keys     : {unexpected or 'NONE'}")
            ok = has_value and has_verify and keys_ok
            print(f"  RESULT: {'PASS' if ok else 'FAIL'}")
            return 0 if ok else 1


if __name__ == "__main__":
    idx = sys.argv[1] if len(sys.argv) > 1 else "FLOPS-H100-OD"
    raise SystemExit(asyncio.run(main(idx)))
