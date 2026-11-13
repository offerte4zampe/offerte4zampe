# Withhold exact price/stock contradictions from commercial publication

Branch: `fix/commercial-discrepancy-suppression`. Base main: `41f43dd387d12cc94ae69de2edcbe7e7d7dc99d4`. No push, merge or deployment performed.

The current audit detects merchant-page price and stock discrepancies but emits warnings and leaves the rows eligible for best-price selection and AggregateOffer. For example, current source evidence identifies Bauzaar Cat&Rina variant56961166115141 at7.64 EUR versus feed7.59 EUR; Isola Fish4Dogs SKU000138596 is OutOfStock on the exact page versus available in the feed. Upstream cause is not established.

## Behavior

The existing audit now withholds a row from the downstream published catalog only when all conditions hold: supported non-Amazon merchant; usable evidence bound to the current row fingerprint; a safe exact page source; status `verified`; exact variant/product ID; no contradictory valid GTIN; evidence no older than24 hours and not future dated; an explicitly compared price/stock field both flagged and actually discordant. Inconclusive, missing, expired, differently sourced, different-row or different-variant evidence cannot suppress a row. Prices/stock are never replaced with guessed values or page defaults.

This follows the existing merchant-link suppression architecture. The original row and proof remain in `site/data/store-audit.json` under `commercial_suppression`, with input/published counts and reasons. The next upstream import reconstructs all rows, so a changed row or expired evidence can return at the normal feed-only evidence level. Expiry is **not** a merchant verification. Existing audit selection prioritizes prior discrepancies for recheck. Previously persisted non-Amazon history is untouched; a known contradicted observation is not added as a new history point. The remaining built catalog then cannot rank a withheld row, describe it as commercially verified, or include it in AggregateOffer.

## Existing links

Removing canonical rows would otherwise change `/go/{id}` behavior. A redirect-only fallback resolves only an exact withheld ID and its original row from the audit. It applies the existing36-hour freshness, raw availability and identity-expiry guards plus an explicit merchant/network allowlist. Archived TradeTracker targets require the current merchant c/m program IDs, publisher a=518044, one parameter each, and a single HTTPS u exactly equal to the original raw merchant URL; wrong or duplicate targets/programs are rejected. Request URL parameters never supply targets. The original affiliate URL string is passed unchanged to the same302 response headers. No price telemetry is recorded for withheld rows. This fallback does not reintroduce the row into comparison, structured offers, shopping lists or social selections.

The report is public just like the original catalog/audit; retained row fields were already public catalog fields and proof fields were already audit fields. No credentials, feed URLs containing secrets or new personal information are added. A missing/malformed audit cannot create a target. Amazon collection, historical exclusion and `PRICE_TRACKING_ENABLED` are unchanged.

## Validation and rollback

`tests/test_commercial_suppression.py` covers exact price/stock contrasts, healthy/inconclusive/expired/future/changed-fingerprint/source/variant/GTIN cases, malformed proofs, unsafe source, Amazon exclusion, unchanged existing history and best-price/index eligibility. Outbound tests cover GET/HEAD, exact affiliate bytes/status/privacy headers, missing route/shard rows, no telemetry, and negative stock/freshness/identity/host guards. The real snapshot test checks all18,041 original offer redirects, including the two withheld IDs removed from routes/shards in its fixture.

`PYTHONPATH=. python docs/operations/verify_commercial_suppression.py` is a read-only simulation against the repository's real snapshot and cache. It writes no generated production artifacts. The companion JSON contains resulting counts and metrics; it is a simulation, not a deployed result. Browser smoke, live HTTP and post-deploy validation remain required before any authorized release.

Rollback is a revert of the logic PR followed by the normal catalog import; never restore stale catalog snapshots or rewrite merchant prices manually. Risk: temporary omission after a legitimate merchant change; bounded by exact row binding, source/identity checks, short evidence TTL and normal reimport. Uncertainty remains for page stock truth versus actual checkout stock, and no checkout is claimed.


## Snapshot result and remaining limits

The read-only simulation using only the cache actually committed on main withholds **one** offer: Isola000138596. Published rows18,041→18,040; multishop products556→555; active canonicals remain16,352. Bauzaar's committed proof exceeds24h at the snapshot timestamp, so it does not suppress from that old proof; a fresh exact check on the next audit must establish the current contradiction before it can be withheld. The separately collected live observation is not silently injected into committed cache. No generated catalog, audit data, source dates or prices were edited for this change.

The fallback adds one audit-asset read only when normal route/product lookup has no row. Normal existing redirects still use the same assets and fast path. Unknown IDs can also incur this extra static-asset read; no external merchant or analytics call is added. The report already exists and may grow with withheld rows; this approach is deliberately scoped and should be reconsidered if a large number of rows is withheld. The fallback never implies price or availability certification and cannot bypass stock/freshness guards. Current program IDs are conservative constants: a future affiliate program change requires review rather than silently broadening acceptance.

Local validation on the final implementation: **314 Python tests passed**, **268 JavaScript tests passed**, `git diff --check` passed. JavaScript snapshot redirect parity covered18,041 offer IDs and16,937 eligible affiliate redirects, with the two commercial example IDs explicitly removed from route/product fixture data to exercise the archive. This does not replace browser smoke or CI on the future PR commit. No production files or generated D1 attestation were committed.
