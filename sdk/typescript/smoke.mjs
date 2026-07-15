/**
 * Dependency-free live contract smoke for @flopsindex/sdk.
 *
 *   node smoke.mjs
 *
 * Verifies the public endpoints the SDK is coded against return the
 * documented envelope shapes. This package ships the public surface only,
 * so this smoke exercises: search, price (global), verify, listIndices.
 * Runs anywhere with global fetch (Node >= 18) — no build, no install.
 * The typed `smoke.ts` is the same checks through the actual SDK.
 */
const BASE = process.env.FLOPS_BASE_URL ?? "https://app.flopsindex.com";
let failures = 0;
const ok = (label, cond, extra = "") => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${label}${extra ? "  " + extra : ""}`);
  if (!cond) failures++;
};
const getJson = async (path) => {
  const r = await fetch(BASE + path, {
    headers: { Accept: "application/json", "User-Agent": "flopsindex-sdk-smoke/0.8.0" },
  });
  return { status: r.status, body: await r.json().catch(() => null) };
};

// 1. search → resolves a real slug (SDK: Client.search)
const search = await getJson("/v1/search?q=H100%20spot&limit=5");
ok("search returns results", search.status === 200 && (search.body?.results?.length ?? 0) > 0,
  `count=${search.body?.count}`);
const slug = search.body?.results?.[0]?.index_id ?? "FLOPS-H100-SPOT";

// 2. price → envelope shape (SDK: Client.getPrice)
const price = await getJson(`/v1/price/${encodeURIComponent(slug)}`);
ok("getPrice has index_id + unit",
  price.status === 200 && Boolean(price.body?.index_id) && Boolean(price.body?.unit),
  `${slug} = ${price.body?.value} ${price.body?.unit}`);

// 3. verify → handshake target (SDK: Client.verify / verifyHandshake)
const v = price.body?.value ?? 0;
const verify = await getJson(`/v1/verify?index_id=${encodeURIComponent(slug)}&value=${v}`);
ok("verify endpoint responds", verify.status === 200 && verify.body !== null);

// 4. listIndices → public catalog (SDK: Client.listIndices)
const cat = await getJson("/v2/catalog/public");
const catLen = Array.isArray(cat.body) ? cat.body.length : (cat.body?.indices?.length ?? cat.body?.count ?? 0);
ok("listIndices returns catalog", cat.status === 200 && Number(catLen) > 0, `entries=${catLen}`);

console.log(`\n${failures === 0 ? "ALL PASS" : failures + " FAILED"}`);
process.exit(failures === 0 ? 0 : 1);
