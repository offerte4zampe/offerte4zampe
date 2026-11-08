"""Regression: Amazon is excluded at ingestion and aggregation boundaries."""
import datetime as dt
import unittest
from automation.price_merchant_policy import price_history_allowed,history_offer_allowed
from automation.update_history import update, write_shards
from automation.build_product_catalog import observed_history

class AmazonHistoryIsolationTests(unittest.TestCase):
    def test_merchant_allowlist_fails_closed(self):
        self.assertFalse(price_history_allowed('amazon'))
        self.assertFalse(price_history_allowed('AMAZON'))
        self.assertFalse(price_history_allowed('new-unapproved-store'))
        self.assertFalse(history_offer_allowed('amazon:ASIN'))
        self.assertTrue(price_history_allowed('bauzaar'))

    def test_import_prunes_existing_amazon_rows_and_never_reintroduces(self):
        stamp='2026-11-08T07:00:00Z'
        old={'offers':{
            'amazon:ASIN':[{'day':'2026-11-07','low':99,'high':99,'last':99,'available':True}],
            'bauzaar:1':[{'day':'2026-11-07','low':10,'high':10,'last':10,'available':True}],
        },'identities':{'amazon:ASIN':'old','bauzaar:1':'old'}}
        cat={'generated_at':stamp,'offers':[
            {'id':'amazon:ASIN','merchant_id':'amazon','price':90,'checked_at':stamp,'available':True},
            {'id':'bauzaar:1','merchant_id':'bauzaar','price':12,'checked_at':stamp,'available':True}
        ]}
        output=update(old,cat,'2026-11-08')
        self.assertNotIn('amazon:ASIN',output['offers'])
        self.assertNotIn('amazon:ASIN',output['identities'])
        self.assertIn('bauzaar:1',output['offers'])

    def test_history_shards_cannot_publish_amazon_even_with_legacy_input(self):
        import tempfile, gzip, hashlib, json
        history={'started_at':'2026-11-08','updated_at':'2026-11-08T07:00:00Z','retention_days':180,
                 'offers':{'amazon:ASIN':[{'day':'2026-11-08','low':1,'high':2}],
                           'bauzaar:1':[{'day':'2026-11-08','low':10,'high':11}]}}
        with tempfile.TemporaryDirectory() as d:
            from pathlib import Path
            write_shards(history,Path(d))
            for file in Path(d).glob('*.json.gz'):
                contents=json.loads(gzip.decompress(file.read_bytes()))
                self.assertNotIn('amazon:ASIN',contents['offers'])

    def test_aggregate_min_max_mean_ignores_amazon(self):
        today='2026-11-08'
        rows=[{'id':'amazon:ASIN','merchant_id':'amazon'},
              {'id':'bauzaar:1','merchant_id':'bauzaar'}]
        history={'offers':{
           'amazon:ASIN':[{'day':today,'low':1,'high':2,'last':1.5,'available':True}],
           'bauzaar:1':[{'day':today,'low':15,'high':16,'last':15.5,'available':True}]
        }}
        result=observed_history(rows,history)
        self.assertEqual(result,[{'day':today,'low':15,'high':16,'sum':15.5,'count':1}])

if __name__=='__main__':
    unittest.main()
