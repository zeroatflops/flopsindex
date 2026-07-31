# @flopsindex/sdk

TypeScript/JavaScript SDK for the [FLOPS Index](https://app.flopsindex.com) —
GPU compute reference rates with verifiable citations.

Zero runtime dependencies. Uses global `fetch` — Node ≥ 18, Deno, Bun,
Cloudflare Workers, browsers. Same method names as the
[Python SDK](https://pypi.org/project/flopsindex/) so you can swap languages
without relearning the API.

**Monorepo** — [flopsindex](https://github.com/zeroatflops/flopsindex) · [Public access overview](https://github.com/zeroatflops/flopsindex#whats-distinctive)

## Public access

This package exposes the **public FLOPS index surface** only: citeable reference rates with verify and permalink URLs. Index construction methodology is not published in this repository — see [flopsindex.com](https://flopsindex.com) and the [public access overview](https://github.com/zeroatflops/flopsindex#whats-distinctive).

| Access | What you get | How (this package) |
|---|---|---|
| **Anonymous (default)** | Delayed public price (~6h grid; indicative, not for settlement) for the FLOPS family — spot, on-demand and DePIN market types, e.g. `FLOPS-H100-OD`, `FLOPS-A100-SPOT`, `FLOPS-A100-DEPIN`. | `new Client()` with no API key |
| **Keyed** | Same endpoints at **real-time, full precision**. | `FLOPSINDEX_API_KEY` or `new Client({ apiKey })` → `X-FLOPS-Api-Key` |
| **Partner** | **Higher fidelity**, expanded coverage, and additional detail beyond the public delayed surface. | [team@flopsindex.com](mailto:team@flopsindex.com) |

If you need more than delayed public rates — e.g. production-grade latency, broader index families, or deeper commercial terms — reach out to **team@flopsindex.com** to discuss partner options.

## Install

```bash
npm install @flopsindex/sdk
```

## Quick start

```ts
import { Client } from "@flopsindex/sdk";

const flops = new Client(); // optional FLOPSINDEX_API_KEY upgrades to real-time

const h100 = await flops.getPrice("FLOPS-H100-OD");
console.log(`${h100.value} ${h100.unit}`); // e.g. 2.40 USD/GPU-hr

const check = await flops.verifyHandshake("FLOPS-H100-OD", h100.value ?? 0);
if ("ok" in check && check.ok === false) {
  // upstream pending / error — your call
} else {
  // verified — cite https://app.flopsindex.com/i/FLOPS-H100-OD
}
```

## Methods

| Method | Endpoint | Returns |
|---|---|---|
| `getPrice(id)` | `/v1/price/{id}` | Latest public price envelope |
| `search(q, limit?)` | `/v1/search` | NL → canonical slug |
| `verify(id, value)` | `/v1/verify` | Citation check (throws on error) |
| `verifyHandshake(id, value?)` | `/v1/verify` | Same as verify, but returns errors instead of throwing |
| `listIndices()` | `/v2/catalog/public` | Live public catalog |

Anonymous callers get the delayed public price; an API key upgrades to real-time — see [Public access](#public-access).

MCP hosts (Claude, Cursor, Windsurf, etc.) should use [`flopsindex-mcp`](https://pypi.org/project/flopsindex-mcp/) instead of this package.

## Error handling

```ts
import { FlopsNotFoundError, FlopsRateLimitError } from "@flopsindex/sdk";

try {
  await flops.getPrice("NOT-A-REAL-SLUG");
} catch (e) {
  if (e instanceof FlopsNotFoundError) { /* unknown slug */ }
  if (e instanceof FlopsRateLimitError) { /* back off e.retryAfterSeconds */ }
}
```

`verifyHandshake` never throws on HTTP errors — it returns
`{ ok: false, reason, upstream_status }` instead, matching the MCP server's
defensive envelope.

## Build & test

```bash
npm install
npm run build      # tsc → dist/ (ESM + .d.ts)
npm run smoke      # typed live smoke (smoke.ts, needs a TS-aware Node)
node smoke.mjs     # dependency-free live contract smoke (no build needed)
```

## Citation

When citing a FLOPS value, include the verify URL from the response:

> FLOPS Index (2026). *{index_name}*. https://app.flopsindex.com/i/{index_id}

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
