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
    def test_home_omits_historical_discount_even_with_saved_observations(self):
        import datetime
        from automation.build_home_data import build, render_home
        now = datetime.datetime(2026,11,7,12,tzinfo=datetime.timezone.utc)
        item = dict(id='m:1', merchant_id='m', merchant='Shop', title='Dog food 2 kg', brand='Brand',
                    category='Dog food', price=10, available=True, checked_at=now.isoformat(),
                    image='https://example.com/p.jpg', url='https://example.com/product', weight_kg=2)
        catalog = dict(offers=[item], sources=[dict(id='m',name='Shop',status='ok',checked_at=now.isoformat())],
                       generated_at=now.isoformat(),refresh_hours=6)
        history={'offers':{'m:1':[dict(day='2026-11-04',last=15),dict(day='2026-11-05',last=15)]}}
        with patch.dict(os.environ, {'PRICE_TRACKING_ENABLED':'false'}):
            result=build(catalog,now,history)
        self.assertNotIn('verified_discount_pct',result['offers'][0])
        self.assertNotIn('verified_before_price',result['offers'][0])

    def test_nested_articles_and_privacy_do_not_promote_disabled_features(self):
        with tempfile.TemporaryDirectory() as td:
            site=Path(td)
            (site/'offerte').mkdir()
            (site/'offerte'/'settimanali.html').write_text('<head></head><a href="/preferiti">Preferiti</a><p>Vedi lo storico dei prezzi</p>')
            (site/'privacy.html').write_text('<head></head><h2>Preferiti e prezzo desiderato</h2><p>Quando salvi un preferito puoi ricevere notifiche.</p><p>La privacy continua.</p>')
            with patch.dict(os.environ, {'PRICE_TRACKING_ENABLED':'false'}):
                apply(site)
            article=(site/'offerte'/'settimanali.html').read_text()
            privacy=(site/'privacy.html').read_text()
            self.assertNotIn('/preferiti',article)
            self.assertNotIn('storico',article.lower())
            self.assertNotIn('Preferiti',privacy)
            self.assertIn('La privacy continua.',privacy)

    def test_redaction_has_no_coupon_side_effects(self):
        html='<a href="/codici-sconto">CIOTOLA30</a><a href="/preferiti">avvisi di prezzo</a>'
        self.assertIn("CIOTOLA30", redact_html(html))
        self.assertNotIn("/preferiti", redact_html(html))

if __name__=="__main__":
    unittest.main()
