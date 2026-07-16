# ChatGPT App (Apps SDK) — feasibility note

**Question:** can we ship a ChatGPT App backed by the *existing* hosted FLOPS MCP server
(`POST https://app.flopsindex.com/mcp`), and is it worth doing now?

**Short answer:** technically close, but a directory-published App needs an Apps-SDK-shaped server,
identity verification, and OpenAI review. The **Custom GPT** (see `custom-gpt.md`) is the fastest path
today; treat the ChatGPT App as **deferred** until we choose to invest in that surface.

## What a ChatGPT App requires
- **An MCP server built with the Apps SDK.** The App's capabilities are its MCP tools. Our hosted server
  already exposes five key-free tools (`list_indices`, `search_indices`, `get_price`, `get_index`,
  `verify`), so the *data plane* is done. The gap is Apps-SDK conventions: structured tool results and,
  for a first-class experience, an inline UI component/widget (e.g. a price card with the verify link).
  A plain MCP server connects fine in **Developer Mode** for testing, but the directory experience
  assumes Apps-SDK output.
- **Identity verification.** Before submitting, the publisher must complete verification in the OpenAI
  Platform dashboard — individual verification to publish under a person's name, or business verification
  to publish under a business name (here: FLOPS Index).
- **Submission + review.** Submissions go through a plugin submission portal and are reviewed against
  OpenAI's App submission guidelines, including MCP connectivity details, testing instructions, directory
  metadata, and country availability. Publication is **gated on that review**, not instant.
- **A reachable, stable server.** We already have one (`https://app.flopsindex.com/mcp`), key-free, which
  satisfies the "publicly reachable MCP endpoint" requirement.

## What we already have working for us
- Live, key-free hosted MCP with five relevant tools and a verify-URL on every value — the exact shape a
  reviewer wants (no auth friction, independently checkable outputs).
- A source-opaque, delayed public surface with clear disclaimers — low policy risk for review.

## What's missing / cost to close
1. Wrap tool outputs in Apps-SDK structured content (small); optionally build one UI widget (moderate).
2. Complete OpenAI identity/business verification for "FLOPS Index" (owner action, lead time varies).
3. Write submission metadata + testing guide, submit, and wait out review.

## Recommendation
- **Now:** ship the **Custom GPT**. It reuses the same public REST endpoints as an Action (no auth), needs
  no Apps-SDK build and no server change, and can be shared by link immediately. (Listing it in the public
  GPT store still requires a verified builder profile, but private/link sharing does not.)
- **Later (deferred):** pursue the ChatGPT App once we decide the surface is worth the Apps-SDK widget
  work + identity verification + review cycle. The hosted MCP is already the backbone, so the increment is
  presentation + compliance, not new infrastructure.

## Uncertainties to confirm before committing
- Exact current Apps-SDK output contract (structured-content fields / widget requirements) — verify against
  `developers.openai.com/apps-sdk` at build time, as it is in beta and evolving.
- Whether a UI widget is *required* for directory acceptance or merely recommended.
- Verification lead time for a business publisher.

Attribution: **FLOPS Index** — github.com/zeroatflops.
