import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]/'automation'))
import isola_feed as m

class IsolaFeedTests(unittest.TestCase):
    def setUp(self):
        # Synthetic fixture, not public offer data.
        self.p = dict(ID='000123',campaignID=31221,name='Ricetta pollo 2,4 Kg',price=dict(currency='EUR',amount=12),
            URL='https://tc.tradetracker.net/?c=31221&a=518044&u=https%3A%2F%2Fwww.isoladeitesori.it%2Fprodotto%2Fricetta%2F000123.html',
            properties=dict(availability=['in_stock'],brand=['Marca'],GTIN=['1234567890128'],deliveryCosts=['5.90']),variations=[])
    def row(self, p=None): return m.normalize({'products':[p or self.p]})[0]
    def test_exact_product_price_and_net_weight(self):
        r=self.row();self.assertEqual(r['id'],'isola-dei-tesori:000123');self.assertEqual(r['price'],12)
        self.assertEqual(r['weight_kg'],2.4);self.assertIsNone(r['shipping_weight_kg']);self.assertIsNone(r['previous_price'])
        self.p['name']='Ricetta pollo 85 gr';self.assertEqual(self.row()['weight_kg'],.085)
        self.p['name']='Lettiera 10 lt';self.assertIsNone(self.row()['weight_kg'])
        self.p['name']='Ricetta 85 gr - 3 pz';self.assertIsNone(self.row()['weight_kg'])
    def test_stock_and_reject_unmapped_or_untrusted_feed(self):
        self.p['properties']['availability']=['out_of_stock'];self.assertFalse(self.row()['available'])
        for key,val in [('campaignID',16143),('variations',[{}]),('price',dict(currency='USD',amount=12)),('URL',self.p['URL'].replace('a=518044','a=999')),('URL',self.p['URL'].replace('000123.html','000124.html'))]:
            p=copy.deepcopy(self.p);p[key]=val
            with self.assertRaises(ValueError):self.row(p)
        with self.assertRaises(ValueError):m.normalize({'products':[self.p,self.p]})
        with self.assertRaises(ValueError):m.normalize({'products':[]})
    def test_multipack_without_verified_price_basis_is_excluded(self):
        p=copy.deepcopy(self.p);p['ID']='000124';p['URL']=p['URL'].replace('000123.html','000124.html%3Fmultipack%3D3')
        rows=m.normalize({'products':[self.p,p]});self.assertEqual(len(rows),1)

    def test_unknown_stock_excludes_only_that_product(self):
        p=copy.deepcopy(self.p);p['ID']='000124';p['URL']=p['URL'].replace('000123.html','000124.html');p['properties']['availability']=[]
        stats={}
        rows=m.normalize({'products':[self.p,p]},stats=stats)
        self.assertEqual([r['id'] for r in rows],['isola-dei-tesori:000123'])
        self.assertEqual(stats['excluded_unknown_availability'],1)
        with self.assertRaises(ValueError):m.normalize({'products':[p]})

    def test_schema_diagnostic_counts_only_names_never_values(self):
        import contextlib
        import io
        p=copy.deepcopy(self.p)
        p['properties']['MPN']=['PRIVATE-MPN-DO-NOT-LOG']
        p['properties']['sku']=['PRIVATE-SKU-DO-NOT-LOG']
        p['URL']='https://example.com/PRIVATE-URL-DO-NOT-LOG'
        p['price']['amount']=987654
        payload={'products':[p,copy.deepcopy(p)]}
        a=m.feed_schema_counts(payload)
        names={x['key']:x['filled'] for x in a['fields']}
        self.assertEqual(names['properties.GTIN'],2)
        self.assertEqual(names['properties.MPN'],2)
        self.assertEqual(names['properties.sku'],2)
        self.assertIn('properties.GTIN',a['identifier_fields'])
        self.assertNotIn('PRIVATE-SKU-DO-NOT-LOG',str(a))
        with self.assertLogs(m.__name__,level='WARNING') as log:
            m.log_feed_schema(payload)
        output='\\n'.join(log.output)
        for secret in ('PRIVATE-MPN-DO-NOT-LOG','PRIVATE-SKU-DO-NOT-LOG','PRIVATE-URL-DO-NOT-LOG','987654','1234567890128'):
            self.assertNotIn(secret,output)
        self.assertEqual(m.normalize({'products':[self.p]}),m.normalize({'products':[copy.deepcopy(self.p)]}))

    def test_schema_diagnostic_best_effort_and_unusual_keys(self):
        result=m.feed_schema_counts({'products':[{'bad\\nkey':'value','properties':{'bad\\nsecret':'value'},'SKU':'SAFE'}]})
        self.assertEqual([x['key'] for x in result['fields']],['SKU','properties'])
        self.assertEqual(m.feed_schema_counts(None)['records'],0)
        m.log_feed_schema(None)
