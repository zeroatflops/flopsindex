/**
 * @flopsindex/sdk — TypeScript/JavaScript SDK for the FLOPS Index.
 *
 * Live GPU compute pricing reference rates with
 * verifiable provenance. Zero runtime dependencies; uses global fetch.
 *
 * @example
 * ```ts
 * import { Client } from "@flopsindex/sdk";
 * const flops = new Client();
 * const h100 = await flops.getPrice("FLOPS-H100-OD");
 * console.log(`${h100.value} ${h100.unit}`);
 * ```
 */
export { Client } from "./client.js";
export {
  FlopsError,
  FlopsAuthError,
  FlopsNotFoundError,
  FlopsRateLimitError,
  FlopsServerError,
} from "./errors.js";
export type {
  ClientOptions,
  Confidence,
  PriceEnvelope,
  VerifyResult,
  VerifyHandshakeResult,
  SearchHit,
  SearchResult,
  CatalogEntry,
  CatalogResponse,
} from "./types.js";
