"""Fail-closed publish gate for Amazon Associates: source snapshots stay in Git.
Run on a disposable deployment working tree only, AFTER generation and BEFORE asset upload.
PRICE_TRACKING_ENABLED=true is reserved for explicit Amazon approval.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
HISTORICAL_PAGES = {"osservatorio-prezzi.html", "leggere-storico-prezzi.html"}
HISTORICAL_DATA = {"price-history.json.gz", "price-observatory.json"}

def enabled():
    return os.environ.get("PRICE_TRACKING_ENABLED", "false").lower() == "true"

def redact_html(html):
    # Hide feature-specific navigation and inline SEO promises. Never modify coupons.
    html = re.sub(r'<a\b[^>]*href=["\'][^"\']*(?:osservatorio-prezzi|leggere-storico-prezzi|/preferiti)[^"\']*["\'][^>]*>.*?</a>', '', html, flags=re.I|re.S)
    html = re.sub(r'(?i)(?:e\s+)?storico\s+(?:dei\s+)?prezzi(?:\s+osservati)?', '', html)
    html = re.sub(r'(?i)avvisi?\s+(?:di\s+)?prezzo', '', html)
    html = re.sub(r'(?i)prezzo\s+desiderato', '', html)
    return html

def apply(site=SITE):
    if enabled():
        return {"enabled": True, "removed_assets": 0, "processed_html": 0}
    # Delete only from the disposable *deploy workspace*; do not commit deletions.
    removed = 0
    for name in HISTORICAL_DATA:
        path = site / "data" / name
        if path.is_file(): path.unlink(); removed += 1
    for directory in [site / "data" / "history"]:
        if directory.is_dir():
            for path in directory.rglob("*"):
                if path.is_file(): path.unlink(); removed += 1
    for name in HISTORICAL_PAGES:
        path = site / name
        if path.exists(): path.unlink(); removed += 1
    changed = 0
    for path in site.glob("*.html"):
        before = path.read_text(encoding="utf-8")
        after = redact_html(before)
        if before != after:
            path.write_text(after, encoding="utf-8")
            changed += 1
    return {"enabled": False, "removed_assets": removed, "processed_html": changed}

if __name__ == "__main__":
    if not os.environ.get("O4Z_DISPOSABLE_BUILD") == "1":
        raise SystemExit("Refusing to mutate tracked snapshots: run only in disposable deploy build (O4Z_DISPOSABLE_BUILD=1)")
    print("Price-feature deploy gate:", apply())
