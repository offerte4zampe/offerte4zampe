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

## Cloudflare API MCP connection (prepared, NOT authorized)

The official remote MCP endpoint is in `cloudflare-mcp.example.json`. Import that example in an MCP client supporting remote HTTP and complete Cloudflare OAuth there. No secrets or account access are present in this repository. The ChatGPT GitHub connector cannot complete Cloudflare OAuth on the user's behalf.

For CI or a machine-to-machine diagnostic, create a **dedicated least-privilege Cloudflare API token**, grant only the read permissions required, and set it as `CLOUDFLARE_MCP_TOKEN` in a secure secret store (never in a committed config, workflow log or chat). Run `node automation/agent/cloudflare-mcp-probe.mjs` in that environment. The probe sends only the MCP `initialize` method, reports a status without response body, and does **not** prove that any account-specific tools have sufficient permissions. A successful probe is not authorization to deploy or publish.

Run isolated regression tests: `node --test automation/agent/*.test.mjs`.

Only after the OAuth/token check and a scoped permissions review should a separate sandboxed Code Mode runtime be connected. Keep dynamic execution disabled for the public production Worker until tested.

## Manual GitHub connectivity check (no production deploy)

The workflow `.github/workflows/cloudflare-mcp-check.yml` can only be launched manually from the GitHub Actions tab. It requires an Actions repository secret named `CLOUDFLARE_MCP_TOKEN` (a limited Cloudflare user or account API token; **never paste the token into a chat or commit it**). For an account token, Cloudflare MCP documents that `Account Resources: Read` is necessary for automatic account identification. Prefer account/Workers read permissions only and restrict resources to the intended Cloudflare account.

1. In GitHub repository Settings → Secrets and variables → Actions → New repository secret, create `CLOUDFLARE_MCP_TOKEN`.
2. In Actions → `Cloudflare MCP connection check (read-only)` → Run workflow, select `main`.
3. The job first runs offline agent regression tests and then calls only the MCP `initialize` method. Its output is a limited status; it does not invoke MCP tools, deploy, publish or verify access to a specific account resource.
4. A successful handshake is only a transport/authentication preliminary check. Follow it with a separately authorized, read-only account-resource check before activating Code Mode.

GitHub Actions never displays the token in the job's regular output, but it is passed to the workflow process, so review workflow changes and secret scope before running.

## Extended Cloudflare monitor

`.github/workflows/cloudflare-worker-monitor.yml` now checks the Worker on push/manual runs and daily at 09:15 UTC and 18:15 UTC (10:15/19:15 CET; 11:15/20:15 CEST). It performs:

- **Deployment state:** Code Mode makes GET requests for Worker metadata and deployment history, reporting the most recent deployment time and number of serving versions. Missing deploy read access is reported as `deploy_status:not_accessible` rather than silently asserting success.
- **Worker errors:** a fixed *read-only GraphQL query* to Cloudflare Analytics for aggregate requests/errors in the preceding 24 hours. The HTTP request is POST but contains only a `query`, never a GraphQL mutation. An alert triggers at 50+ requests, 5+ errors and error rate at least 5%. Without Analytics Read permission it reports `metrics_unavailable` / `metrics_not_authorized` (not zero errors) and leaves the identity/Worker check intact.
- **Telegram:** public GET `/api/telegram/status`, checking initial test delivery, configured recipient, and durable-object halted state. No POST and no messages sent. A day without a new offer is not a failure if the publisher is healthy.

Only aggregated numbers and sanitized statuses are printed, never credentials, Cloudflare account IDs or raw visitor logs. Missing Analytics permissions may require **Account Analytics: Read**, limited to this account. The workflow never mutates Cloudflare and does not deploy the Worker.

Observe the Actions execution and confirm that `deploy_status` and `metrics.status` are `available` and `metrics_available` before considering those checks fully functioning. A workflow success with `not_accessible` means *partial coverage* only.

## Telegram HTTP 403 resolution (read-only)

The old public status route can return HTTP 403 to GitHub-hosted runners even when Telegram is healthy. The scheduled audit now uses the existing Cloudflare MCP credentials to discover **only an already enabled** `zampachiara.<account-subdomain>.workers.dev` hostname via GETs to `/workers/subdomain` and `/workers/scripts/zampachiara/subdomain`. If the custom-domain check is denied, it tries the exact allowlisted `workers.dev` URL. No WAF rules or Worker routing settings are changed; a disabled workers.dev route is never activated. URLs are validated before use and not printed.

The Telegram monitor reports `source:'workers_dev'` if the fallback can read the publisher's actual Durable Object status. If both routes are blocked or the workers.dev URL is disabled, it still reports **unknown**, not a fabricated healthy state. Do not treat a green GitHub job with `status_access_denied` as a verified Telegram delivery.

The Worker audit performs this fallback in the same GitHub Actions step after checking deploy and error metrics. The existing Telegram publisher remains untouched.
