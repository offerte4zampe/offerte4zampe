import datetime
import json
import re
import unittest
from automation.build_matched_pages import groups, structured_data, render, slug_for, valid_gtin


class MatchedPagesTests(unittest.TestCase):
    def setUp(self):
        self.a = dict(id='a',gtin='8009470006276',brand='Monge',title='Food',variant='1 kg',weight_kg=1,price=10,merchant='A',merchant_id='a',url='https://example.com/a',available=True,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        self.b = self.a | dict(id='b',merchant='B',merchant_id='b',price=12)

    def test_manual_review_hold_blocks_static_comparison_without_removing_input(self):
        import datetime as dt
        now=dt.datetime.now(dt.timezone.utc).isoformat()
        a=dict(id='a',merchant_id='a',merchant='A',title='Food',brand='Brand',gtin='4006381333931',weight_kg=2,price=20,available=True,checked_at=now,url='https://a.example/item')
        b=dict(a,id='b',merchant_id='b',merchant='B',url='https://b.example/item')
        self.assertEqual(len(groups([a,b])),1)
        held=dict(b,comparison_review={'review_state':'unverified','review_due':'2020-01-01'})
        self.assertEqual(groups([a,held]),{})
        self.assertEqual(held['price'],b['price'])
        self.assertEqual(held['url'],b['url'])

    def test_checksum_and_strict_identity(self):
        # Use a checksum-valid fixture, independent of a real product identity.
        code='1234567890128'
        self.assertTrue(valid_gtin(code));self.assertFalse(valid_gtin('1234567890129'))
        a=self.a | dict(gtin=code)
        b=self.b | dict(gtin=code,weight_kg=1.0)
        self.assertEqual(len(groups([a,b])),1)
        for changed in [dict(weight_kg=2),dict(brand='Different'),dict(gtin='1234567890129'),dict(checked_at='2020-01-01T00:00:00+00:00')]:
            self.assertEqual(groups([a,b | changed]),{})

    def test_schema_prices_match_visible_rows_and_exclude_unavailable(self):
        key=('1234567890128','1','monge');rows=[self.a,self.b]
        schema=structured_data(key,rows,'test')
        offer=schema['@graph'][1]['offers']
        self.assertEqual((offer['lowPrice'],offer['highPrice'],offer['offerCount']),(10,12,2))
        output=render('<html><head><title>Template</title></head><main></main></html>',key,rows,slug_for(key))
        self.assertIn('10.00 €',output);self.assertIn('12.00 €',output)
        json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>',output)[-1])
        live=structured_data(key,[self.a,self.b | dict(available=False)],'test')['@graph'][1]['offers']
        self.assertEqual(live['offerCount'],1);self.assertEqual(live['highPrice'],10)
        self.assertEqual(len(structured_data(key,[self.a | dict(available=False)],'test')['@graph']),1)
