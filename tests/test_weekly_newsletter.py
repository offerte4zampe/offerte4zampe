import datetime as dt
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation import build_weekly_newsletter as newsletter

NOW = dt.datetime(2026, 10, 28, 10, tzinfo=dt.timezone.utc)

class NewsletterBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / "catalog.json.gz"
        self.output = Path(self.temp.name) / "newsletter.json"
        self.patches = [
            patch.object(newsletter, "CATALOG", self.catalog),
            patch.object(newsletter, "OUTPUT", self.output)
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def write(self, offers, hours=1):
        stamp = (NOW - dt.timedelta(hours=hours)).isoformat()
        self.catalog.write_bytes(gzip.compress(json.dumps({
            "generated_at": stamp,
            "offers": [{**o, "checked_at": o.get("checked_at", stamp)} for o in offers]
        }).encode()))

    def offer(self, n):
        return {
            "title": f"Crocchette cane alimento {n} 2kg", "variant": "2 kg",
            "category": "alimenti secchi cane", "image": f"https://example.org/images/{n}.jpg",
            "merchant": "Negozio", "url": f"https://example.org/item/{n}",
            "available": True, "price": 12 + n, "weight_kg": 2
        }

    def test_generates_three_fresh_offers(self):
        self.write([self.offer(i) for i in range(3)])
        result = newsletter.build(NOW)
        self.assertEqual(len(result["offers"]), 3)
        self.assertTrue(self.output.exists())

    def test_rejects_collars_and_fishing_line_disguised_as_weight(self):
        rows = [self.offer(i) for i in range(3)]
        rows[0].update(title="Asso Doppia Forza Monofilo UltraSoft 83.0kg 1.10mm 60m", weight_kg=83, category="accessori")
        rows[1].update(title="Camon Collare Barriera per Cane Olio di Neem <25kg", weight_kg=25, category="collari")
        rows[2].update(title="Virbac Veggiedent Fresh L Snack Cani >30kg", weight_kg=30, category="snack")
        self.write(rows)
        with self.assertRaises(ValueError):
            newsletter.build(NOW)

    def test_rejects_missing_product_photos(self):
        rows = [self.offer(i) for i in range(3)]
        rows[0]["image"] = ""
        self.write(rows)
        with self.assertRaises(ValueError):
            newsletter.build(NOW)

    def test_rejects_stale_catalog(self):
        self.write([self.offer(i) for i in range(3)], hours=24)
        with self.assertRaises(ValueError):
            newsletter.build(NOW)

    def test_rejects_insufficient_offers(self):
        self.write([self.offer(i) for i in range(2)])
        with self.assertRaises(ValueError):
            newsletter.build(NOW)

    def test_rejects_unavailable_offers(self):
        rows = [self.offer(i) for i in range(3)]
        rows[0]["available"] = False
        self.write(rows)
        with self.assertRaises(ValueError):
            newsletter.build(NOW)

if __name__ == "__main__":
    unittest.main()
