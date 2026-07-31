# flopsindex — CHANGELOG

All notable changes to the `flopsindex` public-read SDK.
Versioning follows semver; semver guarantees apply only at 1.0 and above.

## 0.8.3 — 2026-07-31

Documentation only. No change to the client, its methods, or its behaviour.

- **The README advertised four index ids that do not exist** — `FLOPS-SPOT`,
  `FLOPS-OD`, `FLOPS-DEPIN`, all of which 404. They are market *types*, not
  index ids. Replaced with ids verified live against the public surface:
  `FLOPS-H100-OD`, `FLOPS-A100-SPOT`, `FLOPS-A100-DEPIN`. This page renders on
  PyPI, so the quick-start it shipped could not be followed successfully.
- **Two cross-repo `#public-access` links were dead** and landed at the top of
  the monorepo README. Repointed to the correct section.

## 0.8.2 — 2026-07-15

- Excluded the test suite from the published sdist (packaging hygiene); prior
  releases inadvertently bundled it.
- Documentation hygiene in the README. No change to the SDK's public methods or
  behaviour.

## 0.8.1 — 2026-07-15

- Fixed version drift: the 0.8.0 distribution reported `__version__ = "0.7.0"`
  (so the SDK identified itself as 0.7.0 in its User-Agent). Aligned to 0.8.1.
- Added a version/metadata guard test so the reported version can't drift from
  the package version again.
- Repaired dead documentation links in the README.

## 0.8.0 — 2026-07-14

Interim release. Shipped the public-read methods but reported `__version__` as
`0.7.0` (see 0.8.1).

## 0.7.0 — 2026-05-26

Public-read SDK release. Exposes the public read endpoints only:

- `price(index_id)` — single current value (`GET /v1/price/{slug}`).
- `search(q)` — `GET /v1/search`.
- `list_indices()` (alias `catalog()`) — public catalog (`GET /v2/catalog/public`).
- `verify(index_id, value)` / `verify_handshake(index_id, value)` —
  citation check (`GET /v1/verify`).

API key handling: the client accepts an `api_key` (constructor or
`FLOPSINDEX_API_KEY`). When set it is forwarded as the `X-FLOPS-Api-Key`
header on every request and upgrades the same methods to full-precision
values server-side. No key is ever required.
