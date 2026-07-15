# flopsindex-mcp

<!-- mcp-name: io.github.zeroatflops/flopsindex-mcp -->

[![PyPI version](https://img.shields.io/pypi/v/flopsindex-mcp.svg)](https://pypi.org/project/flopsindex-mcp/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flopsindex-mcp.svg)](https://pypi.org/project/flopsindex-mcp/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/flopsindex-mcp.svg)](https://pypi.org/project/flopsindex-mcp/)
[![Live API](https://img.shields.io/website?label=app.flopsindex.com&url=https%3A%2F%2Fapp.flopsindex.com%2Fv2%2Fcatalog%2Fpublic)](https://app.flopsindex.com/v2/catalog/public)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**See also** — Python SDK [`flopsindex`](https://pypi.org/project/flopsindex/) · TypeScript SDK [`@flopsindex/sdk`](https://www.npmjs.com/package/@flopsindex/sdk) · live catalog [app.flopsindex.com/v2/catalog/public](https://app.flopsindex.com/v2/catalog/public)

MCP server for the FLOPS public compute price indices — catalog, search, price lookup, and verification over stdio. Works with Claude, Cursor, Windsurf, or any MCP-capable host.

**Monorepo** — [flopsindex](https://github.com/zeroatflops/flopsindex) · [Public access overview](https://github.com/zeroatflops/flopsindex#public-access)

## Public access

This package exposes the **public FLOPS index surface** only: citeable reference rates with verify and permalink URLs. Index construction methodology is not published in this repository — see [flopsindex.com](https://flopsindex.com) and the [public access overview](https://github.com/zeroatflops/flopsindex#public-access).

| Access | What you get | How (this package) |
|---|---|---|
| **Anonymous (default)** | Delayed public price (~6h grid; indicative, not for settlement) for the FLOPS family (FLOPS-SPOT, FLOPS-OD, FLOPS-DEPIN). Built for agents, citation, and lookup. | No API key — stdio server or [hosted `/mcp`](https://app.flopsindex.com/mcp) |
| **Keyed** | Same five tools at **real-time, full precision**. | Set `FLOPS_API_KEY` (forwarded as `X-FLOPS-Api-Key`) |
| **Partner** | **Higher fidelity**, expanded coverage, and additional detail beyond the public delayed surface. | [team@flopsindex.com](mailto:team@flopsindex.com) |

If you need more than delayed public rates — e.g. production-grade latency, broader index families, or deeper commercial terms — reach out to **team@flopsindex.com** to discuss partner options.

## Tools

Five public, key-free tools:

| Tool | Description |
|---|---|
| `list_indices` | Enumerate all public FLOPS indices. Optional `family_filter` substring (e.g. `FLOPS-H100`). |
| `search_indices` | Free-text search across the public catalog (resolves to slugs). |
| `get_price` | Latest published price + confidence for one index. |
| `get_index` | Source-opaque public payload — the citation shape (`index_id, value, unit, as_of, data_tier, confidence, verify_url, citation_url, permalink`). Use this when you intend to cite a value. |
| `verify` | Latest published value + verify metadata for a given `index_id`. |

## Resources

Every public index is also exposed as an MCP resource:

| URI | Returns |
|---|---|
| `flops://index/<INDEX_ID>` | Same source-opaque payload as `get_index`, `mimeType: application/json`. |

`list_resources` enumerates one entry per catalog index; `read_resource("flops://index/FLOPS-H100-OD")` resolves the live value.

## Install

```bash
uv tool install flopsindex-mcp
# or
pip install flopsindex-mcp
```

## Setup

Point your MCP host at the server. Config file location depends on the client (Claude Code, Cursor, Windsurf, etc.):

```json
{
  "mcpServers": {
    "flopsindex": {
      "command": "flopsindex-mcp"
    }
  }
}
```

Or use the hosted gateway at `https://app.flopsindex.com/mcp` — same five tools, no local install.

## Environment

| Var | Default | Purpose |
|---|---|---|
| `FLOPS_API_URL` | `https://app.flopsindex.com` | Override base URL |
| `FLOPS_API_KEY` | _(none)_ | Optional. Upgrades the five public tools to full precision. |

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
