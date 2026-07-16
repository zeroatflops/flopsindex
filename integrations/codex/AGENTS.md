# AGENTS.md — GPU compute prices via the FLOPS Index

This guide tells a coding agent (OpenAI Codex, and any agent that reads `AGENTS.md`) how to look up
and **cite** GPU / accelerator rental reference prices using the public **FLOPS Index**. The API is
**key-free** — no auth, no signup. Drop this file at your repo root, or merge this section into an
existing `AGENTS.md`.

## When to reach for FLOPS
- A task needs the cost to rent a GPU — "what's an H100 going for?", "cheapest A100 right now?",
  "on-demand H200 price?".
- Comparing rates across GPUs or market types (spot / on-demand / DePIN).
- Fact-checking a compute price, or producing a citable price with a link a reader can verify.
- Code or config hard-codes a GPU-hour cost that should be sourced or sanity-checked.

## Ground rules
- **Never fabricate a number.** If a call fails or returns null, say so. Report only values the API returns.
- FLOPS values are **indicative reference levels**, delayed ~6h on the public surface, **global**,
  **rounded**, and **source-opaque** (no provider names, sources, counts, or weights). Confidence is a
  **label** (`HIGH` / `MED` / `LOW`), never a number.
- A value is **not** a live quote, **not** a settlement mark, **not** investment advice — carry that
  caveat when you cite one.
- **Every cited price carries a verify URL and a source URL** (see Citation, below).

## Base URL & endpoints (all GET, key-free)

Base: `https://app.flopsindex.com`

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/price/{slug}` | **Authoritative** single-index record + citation/verify URLs. Cite from this. |
| `GET /v2/catalog/public` | Every public index with its value — scan/compare a family. `/v1/price` wins on any disagreement. |
| `GET /v1/search?q={query}` | Matching slugs + citation URLs only (**no value**) — discover slugs, then price them. |
| `GET /v1/verify?index_id={slug}&value={n}` | Fact-check a claimed value against the published mark. |

Slugs: `FLOPS-<ACCELERATOR>-<MARKET>`, market ∈ `SPOT`, `OD`, `DEPIN`. Examples: `FLOPS-H100-SPOT`,
`FLOPS-A100-OD`, `FLOPS-A100-DEPIN`. Don't guess the accelerator list — use search or the catalog.

`/v1/price` envelope: `value`, `unit` ("USD/GPU-hr"), `as_of` (6-hour UTC bucket), `delayed`,
`confidence`, `change_24h` (`UP`/`FLAT`/`DOWN`/`null`), `data_tier`, `verify_url`, `citation_url`,
`methodology_url`, `disclaimer`.

## Workflow

```bash
# 1. Discover a slug (no value returned here)
curl -s "https://app.flopsindex.com/v1/search?q=h100"

# 2. Authoritative price (cite from this)
curl -s "https://app.flopsindex.com/v1/price/FLOPS-H100-SPOT"

# 3. Fact-check a claimed value
curl -s "https://app.flopsindex.com/v1/verify?index_id=FLOPS-H100-SPOT&value=2.33"

# Compare a whole family in one call
curl -s "https://app.flopsindex.com/v2/catalog/public"
```

## Citation (required)
Present the value WITH its `as_of` (UTC), the delayed-reference caveat, and BOTH links. The raw
`verify_url` has no value attached — append `&value={value}` so the link resolves to a real check.

- Verify: `https://app.flopsindex.com/v1/verify?index_id={slug}&value={value}`
- Source: `https://app.flopsindex.com/i/{slug}`

Canonical one-liner:

> **$2.33/GPU-hr** — H100 spot reference (`FLOPS-H100-SPOT`) as of 2026-07-16 12:00 UTC; delayed
> indicative level, not a live quote. Verify:
> https://app.flopsindex.com/v1/verify?index_id=FLOPS-H100-SPOT&value=2.33 · Source:
> https://app.flopsindex.com/i/FLOPS-H100-SPOT

## Cheapest for a chip
Read `/v2/catalog/public`, filter `FLOPS-<CHIP>-*`, take the min `value`, confirm the winner with
`/v1/price`. The family-min is very often a **DEPIN** (decentralized) rate — a different reliability/risk
class than on-demand. Flag it as decentralized and offer the cheapest conventional (SPOT/OD) rate too.

## Also available
- **MCP** (hosted): `POST https://app.flopsindex.com/mcp`. Local: `uvx flopsindex-mcp`.
  Five tools: `list_indices`, `search_indices`, `get_price`, `get_index`, `verify`.
- **SDKs**: `pip install flopsindex` · `npm i @flopsindex/sdk`.

Attribution: **FLOPS Index** — github.com/zeroatflops.
