#!/usr/bin/env python3
"""Build a conservative weekly newsletter; reject non-product and pet-size weights."""
import datetime as dt
import gzip
import json
import sys
from pathlib import Path
from automation.weekly_offer_validation import validate_offer, validate_payload

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "site/data/catalog.json.gz"
OUTPUT = ROOT / "newsletter-approved.json"

def build(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if not CATALOG.exists():
        raise ValueError("Catalog missing")
    catalog = json.loads(gzip.decompress(CATALOG.read_bytes()))
    generated = dt.datetime.fromisoformat(catalog["generated_at"].replace("Z", "+00:00"))
    if generated.tzinfo is None or generated > now or now - generated > dt.timedelta(hours=12):
        raise ValueError("Catalog stale or invalid timestamp")
    seen, offers = set(), []
    for o in catalog.get("offers", []):
        if not o.get("available") or not o.get("title") or not o.get("merchant"):
            continue
        checked = o.get("checked_at")
        try:
            checked_at = dt.datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
            price = float(o["price"])
            weight = float(o["weight_kg"])
        except (ValueError, TypeError, KeyError):
            continue
        if checked_at.tzinfo is None or checked_at > now or now - checked_at > dt.timedelta(hours=12):
            continue
        if not (0 < price < 100000):
            continue
        title = str(o["title"])[:180]
        variant = str(o.get("variant") or "")[:80]
        candidate = {
            "name": title, "format": variant or title, "price": f"{price:.2f} €",
            "shop": str(o["merchant"])[:100], "url": str(o.get("url") or ""),
            "image": str(o.get("image") or ""), "category": str(o.get("category") or ""),
            "weight_kg": weight, "unit_price": price / weight,
        }
        if not validate_offer(candidate):
            continue
        key = (title.casefold(), variant.casefold())
        if key in seen:
            continue
        seen.add(key)
        offers.append(candidate)
    offers.sort(key=lambda x: (x["unit_price"], x["name"]))
    selected = offers[:5]
    if len(selected) < 3:
        raise ValueError("Fewer than 3 safe, fresh, photographed food/litter offers; publication blocked")
    result = {
        "selection_version": 2,
        "verified_on": now.date().isoformat(),
        "subject": f"Offerte da fiutare · {now:%d/%m/%Y}",
        "offers": [{k: v for k, v in o.items() if k != "unit_price"} for o in selected],
        "selection_note": "Catalog freshness and explicit package sizes checked; prices and images not independently live-verified at merchants."
    }
    validate_payload(result)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    try:
        result = build()
        print("Prepared", len(result["offers"]), "catalog offers (merchant pages not live-verified)")
    except (ValueError, KeyError, OSError) as exc:
        OUTPUT.unlink(missing_ok=True)
        print("BLOCKED:", exc, file=sys.stderr)
        sys.exit(1)
