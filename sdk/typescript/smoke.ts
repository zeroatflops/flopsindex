/**
 * Live smoke test for @flopsindex/sdk. Run with a TypeScript-aware
 * Node (>= 22.6 with --experimental-strip-types, or >= 23.6 natively):
 *
 *   node --experimental-strip-types smoke.ts
 *
 * Hits the real public endpoints. Exits non-zero on failure so CI can
 * gate on it. No API key needed — exercises the public surface this
 * package ships: search, getPrice (global), verifyHandshake, listIndices.
 */
import { Client } from "./src/index.ts";

async function main(): Promise<void> {
  const c = new Client();
  let failures = 0;
  const ok = (label: string, cond: boolean, extra = ""): void => {
    console.log(`${cond ? "PASS" : "FAIL"}  ${label}${extra ? "  " + extra : ""}`);
    if (!cond) failures++;
  };

  // 1. search → resolve a real slug
  const search = await c.search("H100 spot", 5);
  ok("search returns results", (search.results?.length ?? 0) > 0, `count=${search.count}`);

  // 2. price → envelope shape
  const price = await c.getPrice("FLOPS-H100-SPOT");
  ok("getPrice has index_id + unit", Boolean(price.index_id) && Boolean(price.unit),
    `${price.value} ${price.unit}`);

  // 3. verifyHandshake → never throws, returns a structured result
  const hs = await c.verifyHandshake("FLOPS-H100-SPOT", price.value ?? 0);
  ok("verifyHandshake returns object", typeof hs === "object" && hs !== null);

  // 4. listIndices → public catalog
  const catalog = await c.listIndices();
  const catLen = Array.isArray(catalog)
    ? catalog.length
    : (catalog.indices?.length ?? catalog.count ?? 0);
  ok("listIndices returns catalog", Number(catLen) > 0, `entries=${catLen}`);

  console.log(`\n${failures === 0 ? "ALL PASS" : failures + " FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("smoke crashed:", e);
  process.exit(1);
});
