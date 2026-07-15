# flopsindex

**Reference rates for compute economics** — public price indices for GPU rentals (spot, on-demand, DePIN). Every published value carries a verify URL your code can check against the public index.

[![PyPI · flopsindex-mcp](https://img.shields.io/pypi/v/flopsindex-mcp?label=flopsindex-mcp)](https://pypi.org/project/flopsindex-mcp/)
[![PyPI · flopsindex](https://img.shields.io/pypi/v/flopsindex?label=flopsindex)](https://pypi.org/project/flopsindex/)
[![npm · @flopsindex/sdk](https://img.shields.io/npm/v/@flopsindex/sdk?label=%40flopsindex%2Fsdk)](https://www.npmjs.com/package/@flopsindex/sdk)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## Try it in one line

```bash
# MCP server (Claude Code, Cursor, Windsurf, ChatGPT desktop, ...)
pip install flopsindex-mcp && claude mcp add flopsindex -- flopsindex-mcp

# Python REST SDK
pip install flopsindex

# TypeScript / JavaScript SDK
npm i @flopsindex/sdk

# Or skip install — hit the hosted MCP gateway
# https://app.flopsindex.com/mcp   (anonymous, zero-config)
```

Or to your agent: *"Get me the current FLOPS price for an H100 on-demand and show me the verify URL."*

---

## What's distinctive

**Source-opaque by contract.** Every public payload returns a `value` plus citation and verify URLs — nothing about how the value was produced.

**One surface, two access modes.**
- **Anonymous** → delayed public price for the published FLOPS index family (`FLOPS-{model}-{OD|SPOT|DEPIN}`), delayed onto a ~6h grid (as_of snaps to 00/06/12/18 UTC). Indicative reference — not for settlement. The citation surface, designed for LLM/agent discovery and academic reference. The family spans many accelerator models (NVIDIA data-center and workstation GPUs plus AMD Instinct), not just H100 — enumerate the live set via [`/v2/catalog/public`](https://app.flopsindex.com/v2/catalog/public); it grows as coverage crosses the ≥3-source floor.
- **Keyed** (`X-FLOPS-Api-Key`) → the same five tools at full precision.

A **partner tier** with higher fidelity and expanded coverage is available — contact `team@flopsindex.com`.

---

## What's in this repo

| Path | What |
|---|---|
| [`mcp/`](mcp/) | The `flopsindex-mcp` server — stdio MCP, 5 public tools (`list_indices` · `search_indices` · `get_price` · `get_index` · `verify`) + a `flops://index/<INDEX_ID>` resource. Published on PyPI. |
| [`sdk/python/`](sdk/python/) | The `flopsindex` Python REST SDK — published on PyPI. |
| [`sdk/typescript/`](sdk/typescript/) | The `@flopsindex/sdk` TypeScript / JavaScript REST SDK — published on npm. |
| [`schema/`](schema/) | `compute-index-spec.v0.1` — the public payload schema (JSON Schema) + a worked example. |
| [`openapi.json`](openapi.json) | OpenAPI 3 description of the public surface. |
| [`llms-full.txt`](llms-full.txt) | Extended public-surface reference for LLM/agent discovery — source-opaque, 6 endpoints, 14-field envelope. Mirror of the hosted `/llms-full.txt`. |

---

## Verify a value yourself

```bash
curl -s https://app.flopsindex.com/v1/price/FLOPS-H100-OD | jq
#   value:            2.95            (USD/GPU-hr, 2dp)
#   unit:             USD/GPU-hr
#   as_of:            2026-07-13T12:00:00Z   (delayed to a ~6h grid: 00/06/12/18 UTC)
#   data_tier:        LIVE
#   confidence:       HIGH            (HIGH | MED, label only)
#   change_24h:       FLAT            (banded: UP | FLAT | DOWN)
#   disclaimer:       indicative reference; not for settlement
#   methodology_url:  /i/FLOPS-H100-OD/methodology
#   verify_url:       /v1/verify?...
#   citation_url:     /cite?...
#   permalink:        /i/FLOPS-H100-OD
#   ... source-opaque public payload only.
```

The same value is reachable via the SDK and via the MCP `get_index` tool — every path returns the same source-opaque payload.

---

## Public surface

| Endpoint | What |
|---|---|
| [`/mcp`](https://app.flopsindex.com/mcp) | Hosted MCP gateway — same 5 public tools, no install |
| [`/v2/catalog/public`](https://app.flopsindex.com/v2/catalog/public) | Public catalog (FLOPS-SPOT, FLOPS-OD, FLOPS-DEPIN) |
| [`/.well-known/agent.json`](https://app.flopsindex.com/.well-known/agent.json) | Agent2Agent (A2A) discovery card |
| [`/llms.txt`](https://app.flopsindex.com/llms.txt) | LLM-discovery manifest |
| [`/llms-full.txt`](https://app.flopsindex.com/llms-full.txt) | Deeper agent-context blob |
| [`/cite`](https://app.flopsindex.com/cite) | Citation guide for AI answer engines |
| [`/i/<INDEX_ID>`](https://app.flopsindex.com/i/FLOPS-H100-OD) | Permalink page with schema.org JSON-LD |
| [`/i/<INDEX_ID>/methodology`](https://app.flopsindex.com/i/FLOPS-H100-OD/methodology) | Public methodology page (linked from `methodology_url`) |
| `/v1/verify` | Verify a published value against the index |

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Apache 2.0 governs the **source code** in this repository (SDKs, MCP server, schema, examples). The underlying price data, the FLOPS trademark, and the hosted index methodology are the proprietary work of FLOPS Index; use of the published APIs is governed by the terms at [flopsindex.com](https://flopsindex.com).

---

## Contributing

- Bug reports + small fixes welcome via Issues / PRs.
- Contributions are welcome. **Use only the public index identifiers from `/v2/catalog/public`.**
- For partner-tier access, contact **team@flopsindex.com**.

---

## Status

| Package | Channel |
|---|---|
| `flopsindex-mcp` | [pypi.org/project/flopsindex-mcp/](https://pypi.org/project/flopsindex-mcp/) |
| `flopsindex` (REST SDK) | [pypi.org/project/flopsindex/](https://pypi.org/project/flopsindex/) |
| `@flopsindex/sdk` | [npmjs.com/package/@flopsindex/sdk](https://www.npmjs.com/package/@flopsindex/sdk) |

Public surface, gateway, and catalog: [app.flopsindex.com](https://app.flopsindex.com).
