# @flopsindex/sdk — CHANGELOG

All notable changes to the `@flopsindex/sdk` TypeScript/JavaScript SDK.
Versioning follows semver; semver guarantees apply only at 1.0 and above.

## 0.9.3 — 2026-07-31

- **The published User-Agent lied about the version.** `SDK_VERSION` was left at
  `"0.9.1"` when the package shipped as 0.9.2, so every request from every 0.9.2
  install reported `@flopsindex/sdk/0.9.1`. The two releases were
  indistinguishable in server-side analytics. The source was corrected after
  0.9.2 was already published, so 0.9.3 is the first artifact that actually
  carries the fix. The guard against it — a test that drives a real request and
  asserts the outgoing `User-Agent` matches `package.json` — landed in that same
  commit, which is exactly why it did not catch the original release.
- **The README advertised four index ids that do not exist** — `FLOPS-SPOT`,
  `FLOPS-OD`, `FLOPS-DEPIN`, all of which 404. They are market *types*, not index
  ids. Replaced with ids verified live: `FLOPS-H100-OD`, `FLOPS-A100-SPOT`,
  `FLOPS-A100-DEPIN`. This page renders on npm, so the quick-start it shipped
  could not be followed successfully.
- **Two cross-repo `#public-access` links were dead.** Repointed.

No API change.

## 0.9.2 — 2026-07-15

- Dropped the misleading `tokens` package keyword — this is a compute-only
  price index, not an inference-token product.
- Corrected the `Confidence` type definition.
- Documentation hygiene. No change to the SDK's public methods or runtime
  behaviour.

## 0.9.1 — 2026-07-15

- Clean rebuild: 0.9.0 embedded a stale `dist/version.js` (pinned to 0.8.0
  because `dist/` was not cleaned between builds). `dist/` is now rebuilt clean
  and reports 0.9.1.
- Repaired dead documentation links in the README.

## 0.9.0 — 2026-07-14

Interim release. Superseded by 0.9.1 (shipped a stale `dist/version.js`).

## 0.8.0 — 2026-05-26

Public-surface SDK. Zero dependencies; runs anywhere with global `fetch`
(Node ≥ 18, Deno, Bun, Cloudflare Workers, browsers).

- **Public methods:** `getPrice(id)`, `search`, `listIndices`, `verify`,
  `verifyHandshake`, plus the error hierarchy (`FlopsError`,
  `FlopsAuthError`, `FlopsNotFoundError`, `FlopsRateLimitError`,
  `FlopsServerError`).
- API key handling: the client accepts an optional `apiKey` (constructor
  or `FLOPSINDEX_API_KEY`), forwarded as the `X-FLOPS-Api-Key` header. A
  key upgrades the same methods to full-precision values.
- `verifyHandshake` returns a defensive envelope
  (`{ ok: false, reason, upstream_status }`) and never throws on HTTP
  errors.
- Live contract verified against prod via `smoke.mjs` / `smoke.ts`.
