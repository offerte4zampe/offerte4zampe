# Read-only agent pilot (Cloudflare Code Mode preparation)

This directory is a **safe first stage**, not a deployed AI agent or an active Cloudflare Code Mode runtime.

`offer-planner.mjs` is a deterministic pure function that consumes already verified catalog records, returns at most 20 review candidates, and always sets `publish: false`. It does not touch production endpoints, credentials, Telegram, or pricing data.

Run: `node --test automation/agent/offer-planner.test.mjs`

## Integration path (not yet enabled)

1. Connect the official Cloudflare API MCP server `https://mcp.cloudflare.com/mcp` using narrowly scoped OAuth or an API token. Do not commit tokens.
2. Build a **separate** Worker using the experimental `@cloudflare/codemode` package and a Dynamic Worker loader. Expose *read-only* tools for catalog snapshot + current source statuses; do not give this runtime arbitrary network access or write-capable bindings.
3. Have the AI-generated plan invoke read-only tools, summarize results and then call the deterministic planner. Require human review before any publishing, partner claims, or changes.
4. Add CI smoke tests, tracing, cost/rate limits and explicit rollback before enabling a schedule. Do not replace the existing 15-minute Telegram cron.
5. Only after observing safe results consider enabling narrowly authorized write actions, with idempotency and source freshness checks.

Cloudflare docs: https://developers.cloudflare.com/agents/tools/codemode/
Official API MCP: https://mcp.cloudflare.com/mcp

No changes to `wrangler.jsonc`, production assets, cron triggers, or Workers routing are needed for this PR.
