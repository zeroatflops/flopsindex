# Integrations

Drop-in ways to use the public, key-free **FLOPS Index** (GPU compute rental
reference prices) from editors, agents, and assistants. Everything here points
at the live public API — no key, no signup.

| Surface | File | What it is |
| --- | --- | --- |
| **Cursor — MCP** | [`../mcp.json`](../mcp.json) | Hosted MCP server entry. Copy the `mcpServers` block into `.cursor/mcp.json` (per-project) or `~/.cursor/mcp.json` (global). Five tools: `list_indices`, `search_indices`, `get_price`, `get_index`, `verify`. |
| **Cursor — Rule** | [`../rules/flopsindex.mdc`](../rules/flopsindex.mdc) | A project rule teaching Cursor's agent when + how to fetch and cite GPU prices. Drop into `.cursor/rules/`. |
| **Codex / AGENTS.md** | [`codex/AGENTS.md`](codex/AGENTS.md) | Guide for OpenAI Codex and any agent that reads `AGENTS.md`. Curl examples + the price → verify → cite workflow. |
| **Custom GPT** | [`openai/custom-gpt.md`](openai/custom-gpt.md) | Paste-ready Custom GPT: name, description, instructions, conversation starters, and a full OpenAPI 3.1 Action schema (Auth = None). |
| **ChatGPT App** | [`openai/chatgpt-app-assessment.md`](openai/chatgpt-app-assessment.md) | Feasibility note on an Apps-SDK App backed by the hosted MCP (deferred; Custom GPT is the fast path today). |

## The public API in one line

Base `https://app.flopsindex.com`, all GET, key-free:

- `GET /v1/price/{slug}` — authoritative single-index record (cite from this)
- `GET /v2/catalog/public` — every public index with its value
- `GET /v1/search?q={query}` — discover slugs (no value)
- `GET /v1/verify?index_id={slug}&value={n}` — fact-check a claimed value

Slugs are `FLOPS-<ACCELERATOR>-<MARKET>` where market is `SPOT`, `OD`, or
`DEPIN` — e.g. `FLOPS-H100-SPOT`. Values are indicative reference levels,
delayed ~6h on the public surface, global, rounded, and source-opaque;
confidence is an ordinal label (`HIGH`/`MED`/`LOW`), never a number. Not a live
quote, not a settlement mark. Every value carries a verify URL for citation.

Also available as packages: `pip install flopsindex-mcp` (MCP server) ·
`pip install flopsindex` (Python SDK) · `npm i @flopsindex/sdk` (TypeScript SDK).

Attribution: **FLOPS Index** — github.com/zeroatflops
