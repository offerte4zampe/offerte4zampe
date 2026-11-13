import copy
import datetime as dt
import gzip
import json
import unittest
from pathlib import Path
from automation.audit_store_integrity import suppress_commercial_conflicts, fingerprint, verify_page, page_url
from automation.build_product_catalog import build
from automation.update_history import update


class CommercialSuppressionTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,13,20,tzinfo=dt.timezone.utc)
        self.offer=dict(id='bauzaar:1',merchant_id='bauzaar',merchant='Bauzaar',title='Food 1 kg',variant='1 kg',brand='Brand',price=10,available=True,gtin='4006381333931',weight_kg=1,url='https://www.bauzaar.it/products/food?variant=1',affiliate_url='https://tc.tradetracker.net/?c=1&m=600171&a=2&u=https%3A%2F%2Fwww.bauzaar.it%2Fproducts%2Ffood%3Fvariant%3D1',checked_at=self.now.isoformat())
        self.catalog=dict(generated_at=self.now.isoformat(),offers=[self.offer])
        body=json.dumps({'variants':[dict(id=1,title='1 kg',price=1100,available=False,barcode='4006381333931')]})
        self.entry=dict(verify_page(self.offer,body),source=page_url(self.offer),checked_at=self.now.isoformat(),fingerprint=fingerprint(self.offer))

    def apply(self,entry=None,offer=None,now=None):
        return suppress_commercial_conflicts(dict(self.catalog,offers=[offer or self.offer]),{self.offer['id']:self.entry if entry is None else entry},now or self.now)

    def test_exact_contradiction_withheld_original_fields_and_proof_preserved(self):
        before=copy.deepcopy(self.catalog);published,report=self.apply()
        self.assertEqual(published['offers'],[])
        self.assertEqual(report['withheld'][0]['offer'],self.offer)
        self.assertEqual(report['withheld'][0]['reasons'],['price','available'])
        self.assertEqual(self.catalog,before)
        self.assertEqual(self.apply()[1],report)

    def test_price_or_stock_alone_suffices_but_confirmed_equal_does_not(self):
        for field in ['price','available']:
            e=copy.deepcopy(self.entry);e['discrepancies']=[field]
            self.assertEqual(len(self.apply(e)[0]['offers']),0)
            e['evidence'][field]=self.offer[field]
            self.assertEqual(len(self.apply(e)[0]['offers']),1)

    def test_expired_future_changed_source_wrong_identity_inconclusive_missing_are_not_conflicts(self):
        cases=[{},dict(self.entry,status='inconclusive'),dict(self.entry,source='https://www.bauzaar.it/products/other.js'),dict(self.entry,fingerprint='changed'),dict(self.entry,checked_at=(self.now-dt.timedelta(hours=24,seconds=1)).isoformat()),dict(self.entry,checked_at=(self.now+dt.timedelta(seconds=1)).isoformat())]
        e=copy.deepcopy(self.entry);e['evidence']['exact_variant']='2';cases.append(e)
        e=copy.deepcopy(self.entry);e['evidence']['gtin']='08011391147122';cases.append(e)
        for e in cases:
            with self.subTest(e=e):self.assertEqual(self.apply(e)[0]['offers'],[self.offer])
        self.assertEqual(self.apply(offer=dict(self.offer,price=12))[0]['offers'][0]['price'],12)
        bad=dict(self.offer,url='https://evil.test/products/food?variant=1');e=dict(self.entry,source=None,fingerprint=fingerprint(bad))
        self.assertEqual(self.apply(e,offer=bad)[0]['offers'],[bad])

    def test_invalid_proof_cannot_suppress_and_amazon_is_never_processed(self):
        e=copy.deepcopy(self.entry);e['evidence'].update(price=True,available='false')
        self.assertEqual(self.apply(e)[0]['offers'],[self.offer])
        o=dict(self.offer,id='amazon:1',merchant_id='amazon');e=dict(self.entry,fingerprint=fingerprint(o));p,r=suppress_commercial_conflicts(dict(self.catalog,offers=[o]),{o['id']:e},self.now)
        self.assertEqual(p['offers'],[o]);self.assertEqual(r['withheld'],[])

    def test_sku_bound_isola_stock_contradiction(self):
        o=dict(self.offer,id='isola-dei-tesori:001',merchant_id='isola-dei-tesori',url='https://www.isoladeitesori.it/prodotto/food/001.html')
        product={'@type':'Product','sku':'001','offers':{'priceCurrency':'EUR','price':'10','availability':'https://schema.org/OutOfStock'}}
        e=dict(verify_page(o,'<script type="application/ld+json">'+json.dumps(product)+'</script>'),source=page_url(o),checked_at=self.now.isoformat(),fingerprint=fingerprint(o))
        p,r=suppress_commercial_conflicts(dict(self.catalog,offers=[o]),{o['id']:e},self.now)
        self.assertEqual(p['offers'],[]);self.assertEqual(r['withheld'][0]['reasons'],['available'])

    def test_existing_history_preserved_without_new_contradicted_observation(self):
        history={'started_at':'2026-11-12','offers':{'bauzaar:1':[{'day':'2026-11-12','low':9,'high':9,'last':9,'available':True,'checked_at':'2026-11-12T12:00:00+00:00'}]}}
        published,_=self.apply();result=update(history,published,'2026-11-13')
        self.assertEqual(result['offers'],history['offers'])

    def test_published_best_price_does_not_include_contradicted_row(self):
        peer=dict(self.offer,id='webpet:2',merchant_id='webpet',merchant='WebPet',price=12,url='https://www.webpet.it/products/food?variant=2')
        catalog=dict(self.catalog,offers=[self.offer,peer]);published,_=suppress_commercial_conflicts(catalog,{self.offer['id']:self.entry},self.now)
        model=build(published,now=self.now)
        self.assertEqual(model['products'][0]['low_price'],12)
        self.assertEqual(model['products'][0]['verified_shop_count'],1)
        self.assertFalse(model['products'][0]['indexable'])

if __name__=='__main__':unittest.main()
