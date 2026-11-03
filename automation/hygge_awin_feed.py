"""Validate a private Hygge/Awin CSV(.gz) feed; emit normalized data for review.

Never commit feed URLs, Awin download tokens or raw exports. This command does
not publish offers or assert that CIOTOLA30 works.
Usage: python automation/hygge_awin_feed.py /private/F3725.csv.gz /tmp/hygge-normalized.json
"""
import csv
import datetime as dt
import gzip
import json
import math
import sys
import re
import os
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
try:
    from .update_catalog import weight
except ImportError:
    from update_catalog import weight

MERCHANT_ID = "hygge"
MERCHANT = "Hygge Pet Food"
ALIASES = {
    "id": ("id", "merchant_product_id", "product_id", "aw_product_id"),
    "title": ("title", "product_name", "name"),
    "price": ("price", "search_price", "store_price"),
    "url": ("link", "merchant_deep_link", "merchant_product_url", "product_url"),
    "affiliate_url": ("aw_deep_link", "aw_product_link"),
    "image": ("image_link", "merchant_image_url", "aw_image_url", "product_image", "image_url"),
    "brand": ("brand", "brand_name"),
    "category": ("google_product_category", "merchant_category", "category_name", "category"),
    "gtin": ("gtin", "ean", "upc"),
    "sku": ("merchant_product_id", "merchant_sku"),
    "availability": ("availability", "in_stock", "stock_status"),
    "currency": ("currency", "search_price_currency"),
}

def value(row, key):
    for alias in ALIASES[key]:
        found = row.get(alias)
        if found is not None and str(found).strip():
            return str(found).strip()
    return ""

def https_url(raw):
    parsed = urlsplit(raw)
    return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password)

def parse_price(raw):
    try:
        cleaned = raw.strip().replace(",", ".")
        cleaned = re.sub(r"\s+EUR$", "", cleaned, flags=re.IGNORECASE)
        v = float(cleaned)
    except (ValueError, AttributeError):
        return None
    return round(v, 2) if math.isfinite(v) and 0 < v < 100000 else None

def stock(raw):
    t = raw.strip().lower()
    if t in ("1", "true", "yes", "y", "in stock", "in_stock", "instock", "available", "disponibile"):
        return True
    if t in ("0", "false", "no", "n", "out of stock", "out_of_stock", "outofstock", "unavailable", "esaurito"):
        return False
    return None

def parse_rows(reader, checked_at):
    headers = {h.lstrip("\ufeff").strip().lower() for h in (reader.fieldnames or [])}
    for required in ("id", "title", "price", "url"):
        if not any(alias in headers for alias in ALIASES[required]):
            raise ValueError("Missing required Awin field: " + required)
    outputs = []
    rejected = {}
    seen = set()
    for original in reader:
        row = {str(k or "").lstrip("\ufeff").strip().lower(): v for k,v in original.items()}
        if row.get("advertiser_id") != "121988":
            raise ValueError("Unexpected Awin advertiser ID")
        rid = value(row, "id")
        title = value(row, "title")
        price = parse_price(value(row, "price"))
        url = value(row, "url")
        currency = value(row, "currency")
        if not rid or not title or price is None or not https_url(url) or urlsplit(url).hostname != "hyggepetfood.com" or (currency and currency.upper() != "EUR"):
            rejected["invalid_identity_price_url_or_currency"] = rejected.get("invalid_identity_price_url_or_currency", 0) + 1
            continue
        if rid in seen:
            raise ValueError("Duplicate merchant product ID: " + rid)
        seen.add(rid)
        available = stock(value(row, "availability"))
        if available is None:
            rejected["unverified_stock"] = rejected.get("unverified_stock", 0) + 1
            continue
        affiliate_url = value(row, "affiliate_url")
        if not affiliate_url or (not https_url(affiliate_url) or urlsplit(affiliate_url).hostname != "www.awin1.com" or parse_qs(urlsplit(affiliate_url).query).get("awinaffid") != ["3126265"] or parse_qs(urlsplit(affiliate_url).query).get("awinmid") != ["121988"]):
            rejected["invalid_affiliate_url"] = rejected.get("invalid_affiliate_url", 0) + 1
            continue
        img = value(row, "image")
        outputs.append({
            "id": MERCHANT_ID + ":" + rid, "merchant": MERCHANT, "merchant_id": MERCHANT_ID,
            "title": title, "variant": "", "brand": value(row, "brand"),
            "category": value(row, "category"), "price": price, "previous_price": None,
            "available": available, "url": url, "affiliate_url": affiliate_url or None,
            "image": img if https_url(img) else "", "sku": value(row, "sku"),
            "gtin": value(row, "gtin"), "feed_gtin": value(row, "gtin"),
            "weight_kg": weight(title), "checked_at": checked_at,
        })
    if not outputs:
        raise ValueError("No valid offers; old catalog must remain unchanged")
    return outputs, rejected

def import_file(path, checked_at=None):
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        offers, rejected = parse_rows(reader, checked_at)
    return {
        "merchant_id": MERCHANT_ID, "source_type": "official_awin_feed",
        "checked_at": checked_at, "offers": offers, "rejected": rejected,
        "coupon": {"code": "CIOTOLA30", "verified": False, "discount_fraction": 0.30,
                   "note": "Conditions and checkout validity must be verified before publishing"},
    }


def collect():
    """Retrieve the private advertiser feed and return rows in catalog source format."""
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    url = os.environ.get("HYGGE_AWIN_FEED_URL", "").strip()
    if not url:
        # Initial verified snapshot is usable until the live private URL is configured.
        # Keep the actual observation time; do not pretend it was refreshed.
        snapshot = Path(__file__).with_name("hygge-snapshot.json")
        try:
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            if data.get("publisher_id") != "3126265" or data.get("advertiser_id") != "121988":
                raise ValueError("Unexpected snapshot owner")
            offers = data["offers"]
            if not offers or any(o.get("merchant_id") != MERCHANT_ID or
                                 o.get("checked_at") != data["checked_at"] or
                                 not https_url(o.get("url", "")) or
                                 not https_url(o.get("affiliate_url", "")) for o in offers):
                raise ValueError("Invalid snapshot rows")
            # Accept only a snapshot close to its real observation time. Never
            # regenerate a fake checked_at on subsequent catalog runs.
            checked = dt.datetime.fromisoformat(data["checked_at"].replace("Z", "+00:00"))
            if not dt.timedelta(minutes=-5) <= dt.datetime.now(dt.timezone.utc)-checked <= dt.timedelta(hours=36):
                raise ValueError("Snapshot expired")
            for offer in offers:
                if offer.get("weight_kg") is None:
                    offer["weight_kg"] = weight(offer["title"])
            return offers, {"id": MERCHANT_ID, "name": MERCHANT, "status": "ok",
                            "checked_at": data["checked_at"], "offers": len(offers),
                            "source": "Awin verified local snapshot",
                            "method": "Feed ufficiale normalizzato"}
        except (ValueError, OSError, KeyError, TypeError):
            return [], {"id": MERCHANT_ID, "name": MERCHANT, "status": "error",
                        "checked_at": now, "offers": 0, "error": "No fresh Awin feed; configure GitHub secret"}
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "ui.awin.com" or not parts.path.startswith("/productdata-darwin-download/publisher/3126265/") or parts.username or parts.password:
        return [], {"id": MERCHANT_ID, "name": MERCHANT, "status": "error",
                    "checked_at": now, "offers": 0, "error": "Unexpected feed URL"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Offerte4ZampeCatalog/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            if response.status != 200:
                raise ValueError("Feed response was not successful")
            blob = response.read(15_000_001)
        if len(blob) > 15_000_000 or not blob.startswith(b"\\x1f\\x8b"):
            raise ValueError("Feed oversized or not gzip")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "hygge.csv.gz"
            path.write_bytes(blob)
            payload = import_file(path, checked_at=now)
        rows = payload["offers"]
        return rows, {"id": MERCHANT_ID, "name": MERCHANT, "status": "ok",
                      "checked_at": now, "offers": len(rows),
                      "source": "Awin product feed", "method": "Feed ufficiale normalizzato"}
    except Exception as exc:
        # Never log a secret-bearing URL or full exception text.
        return [], {"id": MERCHANT_ID, "name": MERCHANT, "status": "error",
                    "checked_at": now, "offers": 0, "error": type(exc).__name__}

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: hygge_awin_feed.py INPUT.csv[.gz] OUTPUT.json")
    result = import_file(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"offers": len(result["offers"]), "rejected": result["rejected"]}))
