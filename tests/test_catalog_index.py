import sys
import gzip
import json
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from build_catalog_index import build

class CatalogIndexTests(unittest.TestCase):
    def test_shards_preserve_comparison_and_commercial_fields(self):
        offers = [dict(id=str(i), title='Cibo', brand='Marca', price=12, url='https://shop.example/item', affiliate_url='https://affiliate.example/exact', shipping_weight_kg=15, quantity_verified=False, feed_unit_pricing_measure='unused') for i in range(7)]
        offers[0]['comparison_review']={'review_state':'unverified','reason':'Exact commercial identity under review'}
        source = dict(offers=offers, generated_at='2026-10-30', refresh_hours=6, sources=[{'id':'shop'}])
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'catalog-index'
            manifest=build(source,directory,3)
            self.assertEqual([s['rows'] for s in manifest['shards']],[3,3,1])
            rows=[]
            for shard in manifest['shards']:
                rows.extend(json.loads(gzip.decompress((directory/Path(shard['path']).name).read_bytes()))['offers'])
            for row in rows:
                self.assertTrue(row['affiliate'])
                self.assertNotIn('affiliate_url',row)
                self.assertNotIn('url',row)
                self.assertEqual(row['shipping_weight_kg'],15)
                self.assertFalse(row['quantity_verified'])
                self.assertNotIn('feed_unit_pricing_measure',row)
            self.assertEqual(next(row for row in rows if row['id']=='0')['comparison_review'],offers[0]['comparison_review'])
            self.assertEqual(manifest,build(source,directory,3))
            self.assertIn('feed_unit_pricing_measure',offers[0])
