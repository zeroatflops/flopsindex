# flopsindex-mcp — CHANGELOG

All notable changes to the `flopsindex-mcp` MCP server. Versioning follows
semver; semver guarantees apply only at 1.0 and above.

## 0.12.2 — 2026-07-15

Maintenance release. No change to the five public tools, their inputs, or their
outputs.

- Removed a non-public implementation detail from the packaged source; the
  distribution now ships only what the public tools need at runtime.
- Documentation hygiene in the README.

## 0.12.1 — 2026-07-15

Post-publish audit corrections. No change to the five public tools' behaviour.

- `get_price` advertised a "compute or inference price index"; the public
  surface is compute-only. Corrected.
- Repaired dead documentation links in the README — a 404 terms page and the
  retired `docs.` / `schema.` subdomains — repointed to resolving URLs and the
  GitHub monorepo.
- `server.json` version aligned to the published package.

## 0.12.0 — 2026-07-14

Interim public-package release, superseded the same day by 0.12.1.

## 0.11.0 — 2026-05-26

Public-package release. The distribution ships exactly the five public,
key-free tools — `list_indices`, `search_indices`, `get_price`,
`get_index`, `verify` — against the public FLOPS surface.

- All five tools work key-free against the delayed public price.
- `FLOPS_API_KEY` (forwarded as `X-FLOPS-Api-Key`) upgrades the same five
  tools to full-precision values.
- The same surface is also reachable via the hosted gateway at
  `https://app.flopsindex.com/mcp` — zero-install, anonymous.
- `get_index` + the `flops://index/<INDEX_ID>` resource return a
  source-opaque public payload (`value`, `verify_url`, `citation_url`,
  `permalink`, etc.).
