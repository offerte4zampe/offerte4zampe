import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.price_feature_gate import apply, redact_html

class PriceFeatureGateTests(unittest.TestCase):
    def test_disabled_build_excludes_deployed_history_without_touching_source(self):
        with tempfile.TemporaryDirectory() as td:
            site = Path(td)
            (site / "data/history").mkdir(parents=True)
            (site / "data/canonical-products").mkdir(parents=True)
            for name in ["price-history.json.gz", "price-observatory.json"]:
                (site / "data" / name).write_bytes(b"preserved only in git")
            (site / "data/history/00.json.gz").write_bytes(b"history")
            (site / "osservatorio-prezzi.html").write_text("<h1>Storico</h1>")
            (site / "preferiti.html").write_text("<h1>Prezzo desiderato</h1>")
            (site / "index.html").write_text('<head><title>Confronto storico prezzi</title></head><body><a href="/preferiti">Avvisi di prezzo</a> Offerte oggi</body>')
            shard = site / "data/canonical-products/00.json"
            shard.write_text(json.dumps({"p":{"history":[{"day":"2026-11-01","low":1}],"offers":[{"price":2}]}}))
            with patch.dict(os.environ, {"PRICE_TRACKING_ENABLED":"false"}):
                result = apply(site)
            self.assertFalse(result["enabled"])
            self.assertFalse((site / "data/history/00.json.gz").exists())
            self.assertFalse((site / "data/price-history.json.gz").exists())
            self.assertFalse((site / "data/price-observatory.json").exists())
            self.assertFalse((site / "osservatorio-prezzi.html").exists())
            self.assertFalse((site / "preferiti.html").exists())
            self.assertNotIn("history", json.loads(shard.read_text())["p"])
            html = (site / "index.html").read_text()
            self.assertNotIn("storico prezzi", html.lower())
            self.assertNotIn('href="/preferiti"', html)
            self.assertIn("Offerte oggi", html)
    def test_enabled_keeps_existing_assets_and_injects_browser_flag(self):
        with tempfile.TemporaryDirectory() as td:
            site=Path(td)
            (site / "index.html").write_text("<html><head></head><body></body></html>")
            with patch.dict(os.environ, {"PRICE_TRACKING_ENABLED":"true"}):
                self.assertTrue(apply(site)["enabled"])
            self.assertIn("O4ZPriceTrackingEnabled=true", (site / "index.html").read_text())
    def test_redaction_has_no_coupon_side_effects(self):
        html='<a href="/codici-sconto">CIOTOLA30</a><a href="/preferiti">avvisi di prezzo</a>'
        self.assertIn("CIOTOLA30", redact_html(html))
        self.assertNotIn("/preferiti", redact_html(html))

if __name__=="__main__":
    unittest.main()
