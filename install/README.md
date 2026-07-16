# Add FLOPS to your agent

**FLOPS Index** is a public, key-free price index for renting GPU compute — spot, on-demand, and DePIN markets. Every value it returns carries a `verify_url` you (or your agent) can check against the live index, so a cited price is never a black box. No API key, no signup, no auth.

Wire it into whatever agent or IDE you already use and ask it about compute prices in plain English.

**Five tools, all key-free:**

| Tool | What it does |
|---|---|
| `list_indices` | Enumerate every public FLOPS index (optional family filter, e.g. `FLOPS-H100`). |
| `search_indices` | Free-text search across the catalog; resolves to index slugs. |
| `get_price` | Latest published price + confidence for one index. |
| `get_index` | Source-opaque citation payload — the shape to use when you intend to cite a value. |
| `verify` | Check a claimed value against the live index. |

**Verify it works:** after adding the server, ask your agent *"what's an H100 going for?"* — it should call FLOPS and answer with a price and a verify link.

Two ways to connect:

- **Hosted (recommended)** — point your client at `https://app.flopsindex.com/mcp` (streamable HTTP, anonymous, zero install). Use this everywhere it's supported.
- **Local** — run the packaged stdio server with `uvx flopsindex-mcp` (needs [uv](https://docs.astral.sh/uv/); `pipx run flopsindex-mcp` or a plain `pip install flopsindex-mcp` then `flopsindex-mcp` also work). Use this for clients that don't take a remote URL.

Pick your client below and copy the snippet into the named file.

---

## Claude Code

Native remote HTTP. Easiest is the CLI:

```bash
claude mcp add --transport http flopsindex https://app.flopsindex.com/mcp
```

Add `--scope project` to write it into a shared `.mcp.json`, or `--scope user` to make it available in every project.

Project file — **`.mcp.json`** in your repo root:

```json
{
  "mcpServers": {
    "flopsindex": {
      "type": "http",
      "url": "https://app.flopsindex.com/mcp"
    }
  }
}
```

The `"type"` field is required — an entry with a `url` but no `type` is treated as a stdio server and skipped. (`"streamable-http"` is accepted as an alias for `"http"`.)

---

## Claude Desktop

Claude Desktop's config file accepts **stdio servers only** — a bare remote `url` won't work there. Two options:

**Option A — add it as a connector (no file editing).** Settings → Connectors → **Add custom connector** → paste `https://app.flopsindex.com/mcp`. This uses the hosted server directly and is the cleanest path.

**Option B — config file via a local stdio bridge.** Edit **`claude_desktop_config.json`**:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Run the packaged server locally with `uvx` (needs [uv](https://docs.astral.sh/uv/)):

```json
{
  "mcpServers": {
    "flopsindex": {
      "command": "uvx",
      "args": ["flopsindex-mcp"]
    }
  }
}
```

Prefer to reach the hosted server instead of running locally? Bridge it with `mcp-remote` (needs Node/npx):

```json
{
  "mcpServers": {
    "flopsindex": {
      "command": "npx",
      "args": ["mcp-remote", "https://app.flopsindex.com/mcp"]
    }
  }
}
```

Restart Claude Desktop after editing.

---

## Cursor

Native remote HTTP. Create **`.cursor/mcp.json`** in your project (or `~/.cursor/mcp.json` for all projects):

```json
{
  "mcpServers": {
    "flopsindex": {
      "url": "https://app.flopsindex.com/mcp"
    }
  }
}
```

Cursor treats an entry with a `url` as a remote server and one with `command`/`args` as stdio — no explicit `type` field is used in the current documented schema.

---

## VS Code (GitHub Copilot, agent mode)

Native remote HTTP. Note VS Code uses the top-level key **`servers`** (not `mcpServers`) and requires `"type": "http"`. Create **`.vscode/mcp.json`** in your workspace:

```json
{
  "servers": {
    "flopsindex": {
      "type": "http",
      "url": "https://app.flopsindex.com/mcp"
    }
  }
}
```

For a global entry, run the **MCP: Open User Configuration** command from the palette and add the same block. Enable agent mode in the Copilot Chat view to use the tools.

---

## Windsurf (Cascade)

Native remote HTTP, but the URL field is named **`serverUrl`** (not `url`). Edit the config via Cascade → **Manage MCP servers**, or directly:

- Windows: `%USERPROFILE%\.codeium\windsurf\mcp_config.json`
- macOS/Linux: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "flopsindex": {
      "serverUrl": "https://app.flopsindex.com/mcp"
    }
  }
}
```

---

## Cline

Native remote HTTP. Cline's transport type is spelled **`streamableHttp`** (camelCase). Open the Cline panel → **MCP Servers** → **Configure MCP Servers** (this opens the file for you), or edit it directly:

- Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- macOS: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "flopsindex": {
      "type": "streamableHttp",
      "url": "https://app.flopsindex.com/mcp",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

The path assumes a standard VS Code install; on VS Code Insiders replace `Code` with `Code - Insiders`. If you're unsure of the location, the **Configure MCP Servers** button always opens the right file.

---

## Roo Code

Native remote HTTP. Roo spells the transport **`streamable-http`** (hyphenated — different from Cline) and uses `alwaysAllow` rather than `autoApprove`. Roo's file is **`mcp_settings.json`** (not `cline_mcp_settings.json`) and lives under a different extension folder. Open Roo → **MCP Servers** → **Edit Global MCP** to have it opened for you, or edit directly:

- Windows: `%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json`
- macOS: `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`

```json
{
  "mcpServers": {
    "flopsindex": {
      "type": "streamable-http",
      "url": "https://app.flopsindex.com/mcp",
      "alwaysAllow": [],
      "disabled": false
    }
  }
}
```

Roo also supports a per-project file at `.roo/mcp.json` in the repo root using the same block.

---

## Continue

Native remote HTTP, configured in YAML. Note `mcpServers` here is a **list** (`- name:`), not a keyed object. Edit **`~/.continue/config.yaml`** (Windows: `%USERPROFILE%\.continue\config.yaml`) and append:

```yaml
mcpServers:
  - name: flopsindex
    type: streamable-http
    url: https://app.flopsindex.com/mcp
```

---

## Goose

Native remote HTTP. Goose calls the transport `streamable_http` and the URL field **`uri`**. Add via the CLI — `goose configure` → **Add Extension** → **Remote Extension (Streaming HTTP)** — or edit the config directly:

- Windows: `%APPDATA%\Block\goose\config\config.yaml`
- macOS/Linux: `~/.config/goose/config.yaml`

Add under the top-level `extensions:` map:

```yaml
extensions:
  flopsindex:
    type: streamable_http
    name: flopsindex
    enabled: true
    uri: "https://app.flopsindex.com/mcp"
    headers: {}
    env_keys: []
    envs: {}
    timeout: 300
```

The extension key and its `name:` field should match.

---

## Gemini CLI

Native remote HTTP — but use the **`httpUrl`** field, not `url`. In Gemini CLI, `url` means SSE and `httpUrl` means streamable HTTP. Edit **`~/.gemini/settings.json`** (Windows: `%USERPROFILE%\.gemini\settings.json`); a project-scoped `.gemini/settings.json` works too:

```json
{
  "mcpServers": {
    "flopsindex": {
      "httpUrl": "https://app.flopsindex.com/mcp"
    }
  }
}
```

---

## Zed

Recent Zed builds support remote servers natively via a `url` field under `context_servers`. Edit **`settings.json`** (Windows: `%APPDATA%\Zed\settings.json`; macOS: `~/.config/zed/settings.json`):

```json
{
  "context_servers": {
    "flopsindex": {
      "url": "https://app.flopsindex.com/mcp"
    }
  }
}
```

If you're on an older build that doesn't recognize the remote `url` form, run the packaged server locally instead:

```json
{
  "context_servers": {
    "flopsindex": {
      "command": "uvx",
      "args": ["flopsindex-mcp"],
      "env": {}
    }
  }
}
```

---

## Warp

Warp adds MCP servers through its UI rather than a file you edit. Go to **Settings → AI → Manage MCP servers → + Add**, choose the CLI Server / paste-JSON option, and paste:

```json
{
  "mcpServers": {
    "flopsindex": {
      "url": "https://app.flopsindex.com/mcp"
    }
  }
}
```

Warp uses one `url` field for both streamable HTTP and SSE; the transport is negotiated with the endpoint.

---

## Not listed? Any MCP client works

Most MCP hosts accept one of two shapes. If yours takes a remote URL, point it at `https://app.flopsindex.com/mcp`. If it's stdio-only, run the packaged server:

```json
{
  "mcpServers": {
    "flopsindex": {
      "command": "uvx",
      "args": ["flopsindex-mcp"]
    }
  }
}
```

---

## Packages

Skip MCP entirely and call the public index from code — same key-free data, same verify URLs:

```bash
uvx flopsindex-mcp        # run the MCP server locally, no install step
pip install flopsindex    # Python REST SDK
npm i @flopsindex/sdk     # TypeScript / JavaScript SDK
```

---

FLOPS Index — public compute price reference. Source and issues: [github.com/zeroatflops](https://github.com/zeroatflops). Live surface: [app.flopsindex.com](https://app.flopsindex.com). Values are indicative reference levels delayed onto a ~6h grid on the public tier — not settlement marks.
