# flopsindex — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/flopsindex.svg)](https://pypi.org/project/flopsindex/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flopsindex.svg)](https://pypi.org/project/flopsindex/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/flopsindex.svg)](https://pypi.org/project/flopsindex/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/website?label=app.flopsindex.com&url=https%3A%2F%2Fapp.flopsindex.com%2Fv2%2Fcatalog%2Fpublic)](https://app.flopsindex.com/v2/catalog/public)
[![Spec](https://img.shields.io/badge/JSON--LD-v0.1-blue)](https://github.com/zeroatflops/flopsindex/tree/main/schema)
[![Docs](https://img.shields.io/badge/docs-github-blue)](https://github.com/zeroatflops/flopsindex)

**See also** — [docs & source](https://github.com/zeroatflops/flopsindex) · MCP server [`flopsindex-mcp`](https://pypi.org/project/flopsindex-mcp/) · [schema](https://github.com/zeroatflops/flopsindex/tree/main/schema) · [Public access overview](https://github.com/zeroatflops/flopsindex#public-access)

```bash
pip install flopsindex
```

Python client for the FLOPS public API — delayed public GPU compute reference rates (indicative, not for settlement). Stdlib only, no dependencies.

## Public access

This package exposes the **public FLOPS index surface** only: citeable reference rates with verify and permalink URLs. Index construction methodology is not published in this repository — see [flopsindex.com](https://flopsindex.com) and the [public access overview](https://github.com/zeroatflops/flopsindex#public-access).

| Access | What you get | How (this package) |
|---|---|---|
| **Anonymous (default)** | Delayed public price (~6h grid; indicative, not for settlement) for the FLOPS family (FLOPS-SPOT, FLOPS-OD, FLOPS-DEPIN). | `Client()` with no API key |
| **Keyed** | Same endpoints at **real-time, full precision**. | `FLOPSINDEX_API_KEY` or `Client(api_key=...)` → `X-FLOPS-Api-Key` |
| **Partner** | **Higher fidelity**, expanded coverage, and additional detail beyond the public delayed surface. | [team@flopsindex.com](mailto:team@flopsindex.com) |

If you need more than delayed public rates — e.g. production-grade latency, broader index families, or deeper commercial terms — reach out to **team@flopsindex.com** to discuss partner options.

## 30-second example

```python
from flopsindex import Client

c = Client()  # no key required

print(c.price("FLOPS-H100-OD"))
# {'index_id': 'FLOPS-H100-OD', 'value': 2.45, 'unit': 'USD/GPU-hr',
#  'as_of': '2026-07-13T12:00:00+00:00',  # delayed to a ~6h grid (00/06/12/18 UTC)
#  'delayed': True, 'data_tier': 'LIVE', 'confidence': 'HIGH',
#  'change_24h': 'FLAT',  # banded: UP | FLAT | DOWN
#  'disclaimer': 'indicative reference; not for settlement',
#  'methodology_url': '.../i/FLOPS-H100-OD/methodology',
#  'verify_url': '...', 'citation_url': '...', 'permalink': '...', 'upgrade': '...'}

print(c.search("h100 spot"))
print(c.list_indices())
```

## Public surface

All methods work without an API key.

| Method                          | Returns                                  |
|---------------------------------|------------------------------------------|
| `price(index_id)`               | latest public price (delayed for anon)   |
| `search(q)`                     | NL → slug results                        |
| `list_indices()` / `catalog()`  | public catalog (`/v2/catalog/public`)    |
| `verify(id, value)`             | does the value match our tick?           |
| `verify_handshake(id, value)`   | defensive citation check (never raises)  |

## API key (optional — upgrades delayed → real-time)

No key is required. If you have one:

```bash
export FLOPSINDEX_API_KEY="flops_xxxxxxxxx"
```

Or pass it directly:

```python
c = Client(api_key="flops_xxxxxxxxx")
```

The SDK forwards it as `X-FLOPS-Api-Key` on every request, which upgrades the delayed public price to real-time, full precision server-side. See [Public access](#public-access) for partner-tier options.

## Citation

Price, verify, cite:

```python
tick = c.price("FLOPS-H100-OD")
check = c.verify_handshake("FLOPS-H100-OD", tick["value"])
if check.get("verified"):
    # use check["source_url"] in your citation
    ...
```

`verify_handshake` won't raise on HTTP errors — it returns `{ok: false, reason, ...}` instead. Use `verify()` if you want exceptions.

## MCP

For Claude, Cursor, Windsurf, etc. use the separate package: `pip install flopsindex-mcp`.

## Naming

- `FLOPS-{model}-{OD|SPOT|DEPIN}` — GPU rental indices (the only family on the public surface)

Use `c.search()` if you don't know the exact slug.

## Errors

```python
from flopsindex import Client, FlopsNotFoundError, FlopsAuthError

c = Client()
try:
    tick = c.price("FLOPS-UNKNOWN-OD")
except FlopsNotFoundError as e:
    print(f"index not found: {e.detail}")
```

Hierarchy: `FlopsError` → `FlopsAuthError` / `FlopsNotFoundError` / `FlopsRateLimitError` / `FlopsServerError`. All errors carry `.status_code` and `.detail`.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
