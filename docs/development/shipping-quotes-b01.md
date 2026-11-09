# Shipping quote states and evidence monitoring

`O4ZTrade.shipping()` preserves the existing `fee`, `total`, `subtotal` and `reason` interface. It adds `status` (`exact`, `range`, `from`, `unknown`) and a visible destination description. Unknown costs never receive zero. Canonical offer quantities use `quantity.verified`; both that flag and the flat legacy `quantity_verified` block totals when false.

Exact quotes use current documented rules, offer freshness and shipping weight where required. The canonical table renders the reason, source and verification date. It does not award a lowest-total badge to minimum/range quotes or treat them as exact totals for sorting.

Optional `quote_bounds` represents **documented bounds only**. It requires `status: "verified"`, an HTTPS `source`, explicit `checked_at`/`verified_until`, matching territory and exact quantity, and any applicable weight constraints. Existing validity and conflict checks run first. Never create bounds by guessing from an expired/conflicting policy. Do not combine bounds with free-shipping thresholds until their application is explicitly modeled.

Example schema (synthetic values, not an actual merchant policy):

```json
{
  "status": "verified",
  "checked_at": "<actual verification timestamp>",
  "verified_until": "<evidence expiry timestamp>",
  "source": "https://merchant.example/shipping",
  "quote_bounds": {
    "kind": "range",
    "territory": "standard",
    "quantity": 1,
    "fee_min": 3,
    "fee_max": 7
  }
}
```

Use `kind: "from"` with `fee_min` and omit `fee_max` for a documented minimum without a known maximum. Results expose `fee_min`, `total_min` and (only for range) `fee_max`, `total_max`; they do not expose exact `fee` or `total`. No production tariff or verification date is changed by this implementation. The D1 seed adapter deliberately rejects unsupported fields; keep any eventual bounds configuration on the JSON path until separately designed and reviewed.

## Read-only monitoring

`python automation/monitor_shipping_rules.py --annotations --output reports/shipping-evidence.json` reports six expected merchants (including Hygge), expiration health and conflicting policies separately. Its default warning window is **14 days / 336 hours**, independent of the validity period of each rule. An expiring/expired/missing policy raises GitHub annotations but exits successfully by default; use `--fail-on-expired` to fail this monitor explicitly. It never updates tariffs, renews evidence or writes the input JSON. `--output` cannot overwrite the source rules.

The separate `shipping-rules-monitor.yml` workflow runs daily and on manual dispatch with `contents: read`, preserves a JSON artifact, and has no deployment, email or database operation. It does not block the catalog build. Human/authorized source verification is still needed before publishing renewed rules; a passing observation report is not proof of checkout pricing.
