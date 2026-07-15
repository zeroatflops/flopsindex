/**
 * FLOPS public read API — TypeScript client.
 * No runtime deps; needs fetch (Node 18+, Deno, Bun, browsers).
 * Same methods as the Python SDK (flopsindex.Client).
 */
import {
  FlopsAuthError,
  FlopsError,
  FlopsNotFoundError,
  FlopsRateLimitError,
  FlopsServerError,
} from "./errors.js";
import type {
  CatalogResponse,
  ClientOptions,
  PriceEnvelope,
  SearchResult,
  VerifyHandshakeResult,
  VerifyResult,
} from "./types.js";

const DEFAULT_BASE_URL = "https://app.flopsindex.com";
const DEFAULT_TIMEOUT_MS = 30_000;
const SDK_VERSION = "0.9.1";

function envApiKey(): string | undefined {
  // Guarded so the SDK works in browsers where `process` is undefined.
  const proc = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
  return proc?.env?.FLOPSINDEX_API_KEY;
}

export class Client {
  private readonly apiKey?: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly userAgent: string;

  constructor(opts: ClientOptions = {}) {
    this.apiKey = opts.apiKey ?? envApiKey();
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.userAgent =
      opts.userAgent ?? `@flopsindex/sdk/${SDK_VERSION} (+https://app.flopsindex.com)`;
  }

  /** Latest public price (delayed without an API key). */
  async getPrice(indexId: string): Promise<PriceEnvelope> {
    return this.get<PriceEnvelope>(`/v1/price/${encodeURIComponent(indexId)}`);
  }

  /** Natural-language → canonical index_id. */
  async search(q: string, limit = 10): Promise<SearchResult> {
    return this.get<SearchResult>("/v1/search", {
      params: { q, limit: String(limit) },
    });
  }

  /** The live public catalog of every published index (GET /v2/catalog/public). */
  async listIndices(): Promise<CatalogResponse> {
    return this.get<CatalogResponse>("/v2/catalog/public");
  }

  /** Verify a value against the latest tick. Throws on non-2xx. */
  async verify(indexId: string, value: number): Promise<VerifyResult> {
    return this.get<VerifyResult>("/v1/verify", {
      params: { index_id: indexId, value: String(value) },
    });
  }

  /**
   * Verify without throwing — returns { ok: false, reason, ... } on errors.
   * Same shape as the MCP server. value is optional.
   */
  async verifyHandshake(
    indexId: string,
    value?: number,
  ): Promise<VerifyHandshakeResult> {
    const params: Record<string, string> = { index_id: indexId };
    if (value !== undefined) params.value = String(value);
    const url = `${this.baseUrl}/v1/verify?${new URLSearchParams(params).toString()}`;
    try {
      const resp = await this.rawFetch(url);
      const text = await resp.text();
      if (resp.ok) {
        try {
          return JSON.parse(text) as VerifyResult;
        } catch {
          return { ok: false, reason: "invalid_json", upstream_status: resp.status, url };
        }
      }
      const code = resp.status;
      const reason =
        code === 401 || code === 403
          ? "auth_required"
          : code === 404
            ? "endpoint_pending"
            : code >= 500
              ? "upstream_http_error"
              : "client_error";
      return { ok: false, reason, upstream_status: code, url };
    } catch (e) {
      return {
        ok: false,
        reason: "network_error",
        url,
        detail: String((e as Error)?.message ?? e).slice(0, 300),
      };
    }
  }

  // HTTP

  private async rawFetch(url: string): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const headers: Record<string, string> = {
      "User-Agent": this.userAgent,
      Accept: "application/json",
    };
    if (this.apiKey) headers["X-FLOPS-Api-Key"] = this.apiKey;
    try {
      return await fetch(url, { headers, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  private async get<T>(
    path: string,
    opts: { params?: Record<string, string> } = {},
  ): Promise<T> {
    let url = this.baseUrl + path;
    if (opts.params && Object.keys(opts.params).length > 0) {
      url += "?" + new URLSearchParams(opts.params).toString();
    }

    let resp: Response;
    try {
      resp = await this.rawFetch(url);
    } catch (e) {
      throw new FlopsError(`network error: ${String((e as Error)?.message ?? e)}`);
    }

    const body = await resp.text();
    if (resp.ok) {
      try {
        return JSON.parse(body) as T;
      } catch {
        throw new FlopsError(`invalid JSON from ${path}`, { statusCode: resp.status });
      }
    }
    this.raiseForStatus(resp.status, body, resp.headers);
    // unreachable
    throw new FlopsError(`unexpected: ${path}`);
  }

  private raiseForStatus(status: number, body: string, headers: Headers): never {
    let detail: unknown = body;
    try {
      detail = JSON.parse(body);
    } catch {
      /* keep raw body */
    }
    let msg = `HTTP ${status}`;
    if (detail && typeof detail === "object" && "detail" in detail) {
      msg += `: ${String((detail as Record<string, unknown>).detail)}`;
    }
    if (status === 401 || status === 403) {
      throw new FlopsAuthError(msg, { statusCode: status, detail });
    }
    if (status === 404) {
      throw new FlopsNotFoundError(msg, { statusCode: status, detail });
    }
    if (status === 429) {
      const retry = Number(headers.get("Retry-After") ?? "60") || 60;
      throw new FlopsRateLimitError(msg, {
        statusCode: status,
        detail,
        retryAfterSeconds: retry,
      });
    }
    if (status >= 500) {
      throw new FlopsServerError(msg, { statusCode: status, detail });
    }
    throw new FlopsError(msg, { statusCode: status, detail });
  }
}
