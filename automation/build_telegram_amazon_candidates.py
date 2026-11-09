#!/usr/bin/env python3
"""Create an Amazon Telegram editorial *review queue* from existing curated ASINs.

Never writes the publishing feed. Never promotes a candidate to reviewed, never
downloads Amazon images, and does not collect prices or availability.
"""
import argparse
import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site/data/amazon-links.json"
DEFAULT_OUTPUT = ROOT / "automation/telegram-amazon-candidates.json"
ASIN = re.compile(r"^[A-Z0-9]{10}$")
BLOCKED = re.compile(
    r"(?i)\b(veterinar|medicat|antiparassitar|farmac|renal|diabet|calmant)\w*"
)


def candidates(registry, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    grouped = {}
    for row in registry.get("links", []):
        asin = row.get("asin")
        if not isinstance(asin, str) or not ASIN.fullmatch(asin):
            continue
        title = row.get("title")
        if not isinstance(title, str) or not 8 <= len(title.strip()) <= 140:
            continue
        if BLOCKED.search(title):
            continue
        try:
            checked = dt.date.fromisoformat(row["checked_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 0 <= (today - checked).days <= 30:
            continue
        # A single ASIN may appear in more than one merchant catalog; emit it once.
        record = grouped.setdefault(asin, {
            "asin": asin, "title": title.strip(),
            "last_catalog_mapping_check": checked.isoformat(),
            "source_match_count": 0, "reviewed_at": None,
            "note": None, "image": None,
            "rights_confirmed": False, "editorial_reviewed": False,
            "publication_ready": False,
        })
        record["source_match_count"] += 1
        if checked.isoformat() > record["last_catalog_mapping_check"]:
            record["last_catalog_mapping_check"] = checked.isoformat()
    return sorted(grouped.values(), key=lambda r: (r["last_catalog_mapping_check"], r["asin"]), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=pathlib.Path, default=SOURCE)
    ap.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = {"purpose": "editorial_review_only_not_a_publishing_feed",
              "candidates": candidates(source)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Amazon editorial candidates: {len(result['candidates'])}; no posts sent")


if __name__ == "__main__":
    main()
