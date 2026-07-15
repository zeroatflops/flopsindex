/**
 * Typed response shapes for the FLOPS public API.
 *
 * These mirror the envelopes documented in the Python SDK and at
 * https://app.flopsindex.com/llms.txt. Fields are optional where the
 * server omits them.
 */

export type Confidence = "HIGH" | "MED" | string;

/** Envelope returned by GET /v1/price/{index_id}. */
export interface PriceEnvelope {
  index_id: string;
  value: number | null;
  unit: string;
  ts: string | null;
  tier?: string;
  confidence?: Confidence;
  verify_url?: string;
  citation_url?: string;
  [key: string]: unknown;
}

/** Result of GET /v1/verify. */
export interface VerifyResult {
  verified?: boolean;
  actual_value?: number;
  delta_pct?: number;
  source_url?: string;
  [key: string]: unknown;
}

/** Same error envelope shape as the MCP server verify path. */
export type VerifyHandshakeResult =
  | VerifyResult
  | {
      ok: false;
      reason:
        | "auth_required"
        | "endpoint_pending"
        | "upstream_http_error"
        | "client_error"
        | "network_error"
        | "invalid_json";
      upstream_status?: number;
      url: string;
      detail?: string;
    };

export interface SearchHit {
  index_id: string;
  family?: string;
  citation_url?: string;
  [key: string]: unknown;
}

export interface SearchResult {
  q: string;
  count: number;
  results: SearchHit[];
}

export interface CatalogEntry {
  index_id: string;
  family?: string;
  unit?: string;
  frequency?: string;
  [key: string]: unknown;
}

export type CatalogResponse =
  | CatalogEntry[]
  | { indices?: CatalogEntry[]; count?: number; [key: string]: unknown };

export interface ClientOptions {
  /**
   * Optional API key. Upgrades the public price from delayed to
   * real-time. Falls back to the FLOPSINDEX_API_KEY env var.
   */
  apiKey?: string;
  /** Base URL. Defaults to https://app.flopsindex.com. */
  baseUrl?: string;
  /** Request timeout in milliseconds. Defaults to 30000. */
  timeoutMs?: number;
  /** Override the User-Agent header. */
  userAgent?: string;
}
