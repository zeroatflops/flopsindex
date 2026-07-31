# flopsindex-mcp — CHANGELOG

All notable changes to the `flopsindex-mcp` MCP server. Versioning follows
semver; semver guarantees apply only at 1.0 and above.

## 0.12.5 — 2026-07-31

Documentation only. No change to the five tools, their inputs, or their outputs.

- **The README advertised four index ids that do not exist.** `FLOPS-SPOT`,
  `FLOPS-OD` and `FLOPS-DEPIN` were presented as the FLOPS family; all three
  return 404. They are market *types*, not index ids — a real id is
  `FLOPS-<model>-<type>`. Replaced with ids verified live: `FLOPS-H100-OD`,
  `FLOPS-A100-SPOT`, `FLOPS-A100-DEPIN`. This page renders on PyPI, so it was
  the first thing a new user read, and following it failed on the first call.
- **Two cross-repo links pointed at a `#public-access` anchor the monorepo
  README does not have**, so both landed at the top of the page. Repointed to
  the section that actually carries the access-mode overview.

## 0.12.4 — 2026-07-31

Security fix. No change to the five public tools, their inputs, or their
outputs for any well-formed index id.

- **An index id supplied by the model could reshape the request path.**
  `index_id` / `slug` were interpolated raw into `/v1/price/{id}`, so
  `../v1/admin/orgs` resolved out of the price route (to `/v1/v1/admin/orgs`)
  and `X?full=1` appended a query string. Because the `X-FLOPS-Api-Key`
  header is attached to every request, a configured key was replayed to
  whichever path was reached — so a prompt-injected model could pull an
  authenticated response back into its own context. The base URL is fixed, so
  this never left the FLOPS host. Ids are now rejected unless they match
  `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`, and are percent-encoded regardless; the
  request is not made at all when an id is malformed. Applies to `get_price`,
  `get_index`, and the `flops://index/<id>` resource.
- **The server advertised the wrong version.** `Server("flopsindex")` carried
  no `version=`, so hosts displayed the `mcp` SDK version (e.g. `1.29.0`)
  instead of the package version — leaving no way to tell a patched install
  from an unpatched one. Now reports `__version__`.

## 0.12.3 — 2026-07-30

Dependency fix — **0.12.2 cannot be installed fresh; upgrade from it.**

- `mcp` was declared `>=1.0.0` with no upper bound. The MCP SDK released
  2.0.0 on 2026-07-28, which removed `Server.list_tools` / `call_tool`, so
  every fresh install crashed at import with
  `AttributeError: 'Server' object has no attribute 'list_tools'`. That broke
  `uvx flopsindex-mcp`, `pip install flopsindex-mcp`, and the install path
  published in the MCP registry. The hosted gateway was unaffected.
- The declared range was wrong at both ends. Bisected against the shipped
  server: `mcp` 1.0.0 and 1.2.1 fail on missing `mcp.server.lowlevel`
  modules; **1.3.0 is the first working version**. Now `mcp>=1.3.0,<2`.
- `httpx` capped at `<1` for the same reason.

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
