/**
 * Unit tests for @flopsindex/sdk Client. Mocked fetch — no network.
 * Run with: npm test  (vitest). Complements smoke.mjs (live contract).
 */
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  Client,
  FlopsNotFoundError,
  FlopsRateLimitError,
  FlopsServerError,
} from "../src/index.js";

/** Build a fake fetch returning a given status + JSON body, capturing the URL+headers. */
function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const calls: { url: string; headers: Record<string, string> }[] = [];
  const fn = vi.fn(async (url: string | URL, init?: RequestInit) => {
    calls.push({
      url: String(url),
      headers: (init?.headers ?? {}) as Record<string, string>,
    });
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: { get: (k: string) => headers[k] ?? null },
      text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
    } as unknown as Response;
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getPrice URL construction", () => {
  it("builds the bare global price path", async () => {
    const { calls } = mockFetch(200, { index_id: "FLOPS-H100-OD", value: 3.1, unit: "USD/GPU-hr" });
    const c = new Client();
    const r = await c.getPrice("FLOPS-H100-OD");
    expect(r.value).toBe(3.1);
    expect(calls[0]!.url).toBe("https://app.flopsindex.com/v1/price/FLOPS-H100-OD");
  });

  it("encodes the index id in the path", async () => {
    const { calls } = mockFetch(200, { index_id: "x", value: 1, unit: "u" });
    await new Client().getPrice("FLOPS H100");
    expect(calls[0]!.url).toBe("https://app.flopsindex.com/v1/price/FLOPS%20H100");
  });
});

describe("auth header behaviour", () => {
  it("omits the key header when no key is set", async () => {
    const { calls } = mockFetch(200, { ok: true });
    await new Client({ apiKey: undefined }).getPrice("X");
    expect(calls[0]!.headers["X-FLOPS-Api-Key"]).toBeUndefined();
  });

  it("sends the key header when a key is set", async () => {
    const { calls } = mockFetch(200, { ok: true });
    await new Client({ apiKey: "k-123" }).getPrice("X");
    expect(calls[0]!.headers["X-FLOPS-Api-Key"]).toBe("k-123");
  });
});

describe("error mapping", () => {
  it("404 → FlopsNotFoundError", async () => {
    mockFetch(404, { detail: "unknown slug" });
    await expect(new Client().getPrice("NOPE")).rejects.toBeInstanceOf(FlopsNotFoundError);
  });

  it("429 → FlopsRateLimitError with retryAfterSeconds from header", async () => {
    mockFetch(429, { detail: "slow down" }, { "Retry-After": "120" });
    try {
      await new Client().getPrice("X");
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(FlopsRateLimitError);
      expect((e as FlopsRateLimitError).retryAfterSeconds).toBe(120);
    }
  });

  it("500 → FlopsServerError", async () => {
    mockFetch(500, { detail: "boom" });
    await expect(new Client().getPrice("X")).rejects.toBeInstanceOf(FlopsServerError);
  });
});

describe("verifyHandshake (defensive, never throws on HTTP error)", () => {
  it("passes through a 200 record", async () => {
    mockFetch(200, { verified: true, actual_value: 3.1, source_url: "u" });
    const r = await new Client().verifyHandshake("FLOPS-H100-OD", 3.1);
    expect("verified" in r && r.verified).toBe(true);
  });

  it("returns endpoint_pending on 404", async () => {
    mockFetch(404, { detail: "x" });
    const r = await new Client().verifyHandshake("X", 1);
    expect("ok" in r && r.ok === false && r.reason === "endpoint_pending").toBe(true);
  });

  it("returns auth_required on 403", async () => {
    mockFetch(403, { detail: "x" });
    const r = await new Client().verifyHandshake("X", 1);
    expect("ok" in r && r.ok === false && r.reason === "auth_required").toBe(true);
  });

  it("returns network_error when fetch throws", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("ECONNREFUSED"); }));
    const r = await new Client().verifyHandshake("X", 1);
    expect("ok" in r && r.ok === false && r.reason === "network_error").toBe(true);
  });
});

describe("search / verify / listIndices paths", () => {
  it("search hits /v1/search with q + limit", async () => {
    const { calls } = mockFetch(200, { q: "h100", count: 0, results: [] });
    await new Client().search("h100", 5);
    expect(calls[0]!.url).toContain("/v1/search?");
    expect(calls[0]!.url).toContain("q=h100");
    expect(calls[0]!.url).toContain("limit=5");
  });

  it("verify hits /v1/verify with index_id + value", async () => {
    const { calls } = mockFetch(200, { verified: true });
    await new Client().verify("FLOPS-H100-OD", 3.1);
    expect(calls[0]!.url).toContain("/v1/verify?");
    expect(calls[0]!.url).toContain("index_id=FLOPS-H100-OD");
    expect(calls[0]!.url).toContain("value=3.1");
  });

  it("listIndices hits the public catalog", async () => {
    const { calls } = mockFetch(200, []);
    await new Client().listIndices();
    expect(calls[0]!.url).toBe("https://app.flopsindex.com/v2/catalog/public");
  });
});

// The SDK deliberately ENCODES rather than rejects an odd index id (see
// "encodes the index id in the path" above) -- it is a developer-facing
// client, not a model-facing one. The reject-then-encode guard lives in the
// MCP server and the langchain tools, where the id is model-authored.
// What IS pinned here: the User-Agent version must track package.json. It had
// drifted (SDK_VERSION 0.9.1 vs package 0.9.2).
describe("version identity", () => {
  it("reports the same version as package.json in its User-Agent", async () => {
    const { calls } = mockFetch(200, { index_id: "x", value: 1 });
    await new Client().getPrice("FLOPS-H100-OD");
    const pkgVersion = JSON.parse(
      readFileSync(new URL("../package.json", import.meta.url), "utf8"),
    ).version;
    expect(calls[0].headers["User-Agent"]).toContain(
      `@flopsindex/sdk/${pkgVersion}`,
    );
  });
});
