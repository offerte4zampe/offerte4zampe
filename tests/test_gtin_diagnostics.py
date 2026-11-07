"""Offline diagnostics checks; no merchant access."""
import html
import json
import unittest

from automation.gtin_diagnostics import gtin_counters, valid_gtin
from automation.paco_feed import normalize, verify_quantity, verification_plan
import datetime as dt

def fixture():
    return {'products': [{
        'ID':'123', 'campaignID':24833, 'name':'Test cibo',
        'price':{'currency':'EUR','amount':24},
        'URL':'https://www.pacopetshop.it/directlinking/?tt=24833_1216771_518044_&r=https%3A%2F%2Fwww.pacopetshop.it%2Fit%2Fbrand%2F123-test.htm',
        'properties':{'availability':['out of stock'],'sale_price':['20.00 EUR'],'GTIN':['4006381333931'],'brand':['Brand']},
        'variations':[]
    }]}

class GtinDiagnosticsTest(unittest.TestCase):
    def test_checksum_and_exclusive_buckets(self):
        self.assertTrue(valid_gtin('4006381333931'))
        self.assertFalse(valid_gtin('4006381333932'))
        original=[{'feed_gtin':'4006381333931','gtin':''},
                  {'feed_gtin':'4006381333932','gtin':'ignored'},
                  {'feed_gtin':'','gtin':'4006381333931'},
                  {'feed_gtin':None}]
        snapshot=json.dumps(original,sort_keys=True)
        self.assertEqual(gtin_counters(original),dict(raw_present=2,valid=1,invalid=1,empty=2))
        self.assertEqual(json.dumps(original,sort_keys=True),snapshot)

    def test_paco_result_is_identical_with_and_without_diagnostics(self):
        row=normalize(fixture())[0]
        product={'price_amount':20,'attributes':{'1':{'name':'24x85 gr','ean13':row['feed_gtin']}}}
        def page():
            return '<div data-product="'+html.escape(json.dumps(product),quote=True)+'">'
        for reason,edit in [
            (None, lambda:None),
            ('ean_mismatch',lambda:product['attributes']['1'].update(ean13='9999999999999')),
            ('price_mismatch',lambda:product.update(price_amount=21)),
            ('ambiguous_quantity',lambda:product['attributes'].update({'2':{'name':'2 kg','ean13':row['feed_gtin']}})),
            ('unparseable_weight',lambda:product['attributes']['1'].update(name='0 kg')),
        ]:
            product={'price_amount':20,'attributes':{'1':{'name':'24x85 gr','ean13':row['feed_gtin']}}}
            edit()
            seen={}
            now=dt.datetime(2026,11,7,12,tzinfo=dt.timezone.utc)
            plain=verify_quantity(row,page(),now=now)
            audited=verify_quantity(row,page(),now=now,diagnostics=seen)
            self.assertEqual(audited,plain)
            self.assertEqual(seen.get('reason'),reason)
        seen={}
        self.assertEqual(verify_quantity(row,'<div></div>',diagnostics=seen),row)
        self.assertEqual(seen['reason'],'missing_product_data')

    def test_planning_budget_and_outputs_unchanged(self):
        now=dt.datetime(2026,11,7,tzinfo=dt.timezone.utc)
        rows=[dict(normalize(fixture())[0],id='paco:'+str(i)) for i in range(85)]
        first=[dict(r) for r in rows]
        second=[dict(r) for r in rows]
        prior=verification_plan(first,[],set(),now)
        diagnostics={}
        instrumented=verification_plan(second,[],set(),now,diagnostics=diagnostics)
        self.assertEqual(instrumented,prior)
        self.assertEqual(second,first)
        self.assertEqual(diagnostics,dict(skipped_limit=5,reused_proof=0))
        self.assertEqual(len(instrumented),80)

if __name__ == '__main__':
    unittest.main()
