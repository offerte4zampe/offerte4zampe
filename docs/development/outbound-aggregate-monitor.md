# P1 — Merchant click aggregate readout

Problem: GA4 excludes /go/; absent GA4 events cannot certify zero merchant clicks.
The existing Cloudflare read-only monitor can query its already-authenticated
account without exporting credentials or creating another scheduled automation.

The fixed Analytics Engine SQL SELECT reads only merchant-level SUM(_sample_interval)
from offerte4zampe_outbound for the previous seven complete seconds-aligned UTC days.
The SQL endpoint uses POST for read-only SELECT, distinct from MCP's existing GETs.
Reference: https://developers.cloudflare.com/analytics/analytics-engine/sql-api/

No IP, visitor identifiers, product/offer/page fields or prices are queried. Output
is a sampled estimate of consented tracked redirects, not unique visitors, all
clicks, sales or commissions. Worker consent/DNT/GPC/prefetch filtering is unchanged.
HTTP failures, absent dataset, malformed/overlarge results and insufficient access
remain unknown. Successful empty results produce no_rows without a zero total.
More than 100 merchant groups fails closed instead of publishing a truncated total.

Uses existing CLOUDFLARE_MCP_TOKEN only after existing whoami/account validation.
If it lacks Account Analytics read access, report not_authorized; do not broaden
permissions, create tokens or modify secrets. The readout has no local credentials;
actual access/data remain unverified until a permitted runner executes it.

No new workflow/schedule, production Worker, catalog, redirect, tracking, Amazon,
newsletter or account settings change. A missing aggregate warns independently of
Worker health. Existing production deployment protections remain unchanged.

Validation: full agent offline test suite with mocked SQL transport, negative HTTP,
malformed/schema/duplicate/overflow/truncation tests and resolved-account integration.
Rollback: revert this PR (or disable enableOutbound); existing monitor continues.
No merge or deployment is authorized by preparing this branch/PR.
