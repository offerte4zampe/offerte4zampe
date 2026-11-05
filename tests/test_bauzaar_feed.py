import copy
import datetime as dt
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('bauzaar_feed',Path(__file__).parents[1]/'automation/bauzaar_feed.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FeedTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,19,tzinfo=dt.timezone.utc)
        self.p=dict(campaignID=16143,ID='feed-id',name='Ricetta pollo - confezione da 24 pezzi - 1° ORDINE? CODICE',
            URL='https://tc.tradetracker.net/?c=16143&a=518044&m=600171&u=https%3A%2F%2Fwww.bauzaar.it%2Fproducts%2Fpollo%3Fvariant%3D123',
            price=dict(currency='EUR',amount=20),properties=dict(availability=['in stock'],unit_pricing_measure=['1ct']))
    def row(self,p=None): return m.normalize({'products':[p or self.p]},self.now)[0]
    def test_exact_variant_tracking_and_pack_title(self):
        o=self.row();self.assertEqual(o['id'],'bauzaar:123');self.assertTrue(o['url'].endswith('?variant=123'))
        self.assertIn('24 pezzi',o['title']);self.assertNotIn('CODICE',o['title']);self.assertIsNone(o['weight_kg'])
    def test_generic_syndication_suffix_is_not_product_identity(self):
        self.p['name']='Acana Wild Coast 2 kg - Croccantini per cani - Croccantini per gatti - 1° ORDINE? CODICE'
        self.assertEqual(self.row()['title'],'Acana Wild Coast 2 kg')
    def test_explicit_net_weight_only(self):
        self.p['properties']['unit_pricing_measure']=['1,5kg'];self.assertEqual(self.row()['weight_kg'],1.5)
        self.p['properties']['unit_pricing_measure']=['10l'];self.assertIsNone(self.row()['weight_kg'])
    def test_only_current_sale_no_claimed_discount(self):
        self.p['properties'].update(sale_price=['15'],sale_price_effective_date=['2026-10-18T00:00:00+00:00/2026-10-20T00:00:00+00:00'])
        self.assertEqual(self.row()['price'],15);self.assertIsNone(self.row()['previous_price'])
        self.p['properties']['sale_price_effective_date']=['2026-09-18T00:00:00+00:00/2026-09-20T00:00:00+00:00']
        self.assertEqual(self.row()['price'],20)
    def test_reject_invalid_feed_without_replacing_catalog(self):
        for field,v in [('URL',self.p['URL'].replace('a=518044','a=999')),('price',dict(currency='USD',amount=20))]:
            p=copy.deepcopy(self.p);p[field]=v
            with self.assertRaises(ValueError):self.row(p)
        with self.assertRaises(ValueError):m.normalize({'products':[]},self.now)
        with self.assertRaises(ValueError):m.normalize({'products':[self.p,self.p]},self.now)
    def test_out_of_stock_not_available(self):
        self.p['properties']['availability']=['out of stock'];self.assertFalse(self.row()['available'])


    def test_invalid_price_row_does_not_freeze_valid_rows(self):
        bad=copy.deepcopy(self.p);bad['URL']=bad['URL'].replace('variant%3D123','variant%3D124');bad['price']['amount']=0
        rows=m.normalize({'products':[self.p,bad]},self.now)
        self.assertEqual([r['id'] for r in rows],['bauzaar:123'])
        with self.assertRaises(ValueError):m.normalize({'products':[bad]},self.now)

    def test_active_sale_keeps_reference_bound_to_same_variant_and_expiry(self):
        self.p['properties']['sale_price']=['15']
        self.p['properties']['sale_price_effective_date']=['2026-10-18T00:00:00+00:00/2026-10-20T00:00:00+00:00']
        row=self.row();p=row['merchant_promotion']
        self.assertEqual((p['price_cents'],p['reference_cents']),(1500,2000))
        self.assertEqual(p['offer_id'],row['id']);self.assertEqual(p['valid_until'],'2026-10-20T00:00:00+00:00')
        self.p['properties']['sale_price_effective_date']=['2026-09-18T00:00:00+00:00/2026-09-20T00:00:00+00:00']
        self.assertNotIn('merchant_promotion',self.row())
