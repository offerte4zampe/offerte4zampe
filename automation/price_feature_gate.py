"""Fail-closed publish gate for Amazon Associates: source snapshots stay in Git.
Run on a disposable deployment working tree only, AFTER generation and BEFORE asset upload.
PRICE_TRACKING_ENABLED=true is reserved for explicit Amazon approval.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
HISTORICAL_PAGES = {"osservatorio-prezzi.html", "leggere-storico-prezzi.html", "preferiti.html"}
HISTORICAL_DATA = {"price-history.json.gz", "price-observatory.json"}

def enabled():
    return os.environ.get("PRICE_TRACKING_ENABLED", "false").lower() == "true"

def redact_html(html):
    """Remove disabled-feature links and rewrite price-history promises, not generic shipping notices."""
    # Preserve the parent nav/list layout; remove the entire anchor only.
    html = re.sub(r'<a\b[^>]*href=["\'][^"\']*(?:osservatorio-prezzi|leggere-storico-prezzi|/preferiti)(?:\.html)?[^"\']*["\'][^>]*>.*?</a>', '', html, flags=re.I|re.S)
    # Do not recreate historical indicators as allegedly verified retailer discounts.
    html = re.sub(r'<(?:div|section)\b[^>]*class=["\'][^"\']*(?:observed-history|history-chart|history-summary)[^"\']*["\'][^>]*>.*?</(?:div|section)>', '', html, flags=re.I|re.S)
    html = re.sub(r'<div\b[^>]*data-history-offer=[^>]*>\s*</div>', '', html, flags=re.I)
    replacements = [
        (r'(?i)\b(?:minimo|massimo)\s+storico\b', ''),
        (r'(?i)\b(?:storico\s+(?:dei|del|di)\s+prezz\w*|storico\s+prezzi|storico\s+del\s+prezzo)\b', 'prezzi correnti'),
        (r'(?i)\b(?:storico|storici|storica|storiche)\b', ''),
        (r'(?i)\b(?:avvisi?\s+(?:di\s+)?prezzo|alert\s+(?:di\s+)?prezzo|prezzo\s+desiderato|soglia\s+di\s+prezzo)\b', ''),
        (r'(?i)\b(?:buon\s+momento\s+per\s+comprare|prezzo\s+pi[uù]\s+basso\s+di\s+sempre)\b', ''),
        (r'(?i)\b(?:ribassi?\s+(?:storici?|di\s+prezzo)|monitoraggio\s+(?:dei\s+)?prezzi|monitora(?:re)?\s+(?:il|i|l.andamento\s+dei)\s+prezz\w*)\b', ''),
    ]
    for pattern, replacement in replacements:
        html = re.sub(pattern, replacement, html)
    return html

def apply(site=SITE):
    if enabled():
        # Browser widgets are opt-in only; Worker must have the same runtime flag.
        for path in site.glob("*.html"):
            html = path.read_text(encoding="utf-8")
            if "O4ZPriceTrackingEnabled" not in html:
                path.write_text(html.replace("<head>", "<head><script>window.O4ZPriceTrackingEnabled=true</script>", 1), encoding="utf-8")
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
    # Product JSON shards currently carry a historical series: strip only from
    # disposable published assets, leaving committed source JSON untouched.
    import json
    for path in (site / "data" / "canonical-products").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for product in data.values():
                if isinstance(product, dict): product.pop("history", None)
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
