import datetime as dt
import unittest
from automation.build_product_catalog import build
from automation.matching_evidence import description_evidence
from automation.matching_candidates import incompatible

class SupplementaryMatchingTests(unittest.TestCase):
    now=dt.datetime(2026,11,12,12,tzinfo=dt.timezone.utc)
    def row(self,shop,title,**extra):
        return dict(id=shop+':1',merchant_id=shop,merchant=shop,title=title,variant='1 kg',brand='Bunny',weight_kg=1,price=10,available=True,url='https://example.org/'+shop,checked_at=self.now.isoformat(),**extra)
    def model(self,a,b):
        return build({'offers':[a,b],'generated_at':self.now.isoformat()},now=self.now)
    def test_merchandising_noun_does_not_block_exact_characteristics(self):
        a=self.row('a','Bunny Sogno Young 1 kg',gtin='')
        b=self.row('b','Bunny Mangime Sogno Young 1 kg',gtin='')
        result=self.model(a,b)
        self.assertEqual(result['metrics']['multi_shop_products'],1)
        self.assertTrue(all(not o.get('gtin') for o in result['offers']))
        self.assertEqual([o['price'] for o in result['offers']],[10,10])
    def test_variant_differences_never_merge_even_with_shared_photo(self):
        for left,right in [('Young Pollo','Young Trota'),('Young','Senior'),('Renal Care','Struvite Care'),('Talco Care','Lavanda Care'),('Small Care','Large Care'),('60x60 Care','60x90 Care')]:
            with self.subTest(left=left):
                result=self.model(self.row('a','Bunny Sogno '+left,gtin='',image='https://example.org/same.jpg'),self.row('b','Bunny Sogno '+right,gtin='',image='https://example.org/same.jpg'))
                self.assertEqual(result['metrics']['multi_shop_products'],0)
    def test_unknown_quantity_and_conflicting_gtins_block_join(self):
        a=self.row('a','Bunny Sogno Young',gtin='4006381333931')
        for b in [self.row('b','Bunny Mangime Sogno Young',gtin='',quantity_verified=False),self.row('b','Bunny Mangime Sogno Young',gtin='8000500310427')]:
            self.assertEqual(self.model(a,b)['metrics']['multi_shop_products'],0)
    def test_same_shop_is_not_candidate_or_multishop(self):
        a=self.row('a','Bunny Sogno Young',gtin='')
        b={**a,'id':'a:2','title':'Bunny Mangime Sogno Young'}
        result=self.model(a,b)
        self.assertEqual(result['matching_candidates'],[])
        self.assertEqual(result['metrics']['multi_shop_products'],0)
    def test_description_is_fingerprint_not_copied_html_or_identity(self):
        words=' '.join('caratteristica'+str(i) for i in range(25))
        a=description_evidence('<p>'+words+'</p><script>secret</script>','https://example.org/a',self.now.isoformat())
        b=description_evidence(words,'https://example.org/a',self.now.isoformat())
        self.assertEqual(a['sha256'],b['sha256'])
        self.assertNotIn('text',a)
        self.assertEqual(a['scope'],'product_description_not_selected_variant')
        self.assertIsNone(description_evidence('breve slogan','https://example.org/a',''))
        self.assertIsNone(description_evidence(words,'http://example.org/a',''))
    def test_protected_dimensions_and_recipe(self):
        self.assertTrue(incompatible({'sogno','pollo'},{'sogno','trota'}))
        self.assertTrue(incompatible({'60x60'},{'60x90'}))
    def test_photo_uses_original_url_cache_and_requires_permission(self):
        import tempfile,hashlib
        from pathlib import Path
        from PIL import Image
        from automation.matching_evidence import image_fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            site=Path(tmp);(site/'img/p').mkdir(parents=True)
            url='https://images.example.org/original.jpg'
            offer={'merchant_id':'a','image':url,'image_local':'/img/p/shared-400.webp'}
            rule={'allow_cache':True,'permission_status':'verified','evidence':'https://example.org/license','hosts':['images.example.org']}
            Image.new('RGB',(20,20),'red').save(site/'img/p/shared-400.webp')
            self.assertIsNone(image_fingerprint(offer,site,{'a':rule}))
            path=site/'img/p'/(hashlib.sha256(url.encode()).hexdigest()[:24]+'-400.webp')
            Image.new('RGB',(20,20),'blue').save(path)
            self.assertIsNotNone(image_fingerprint(offer,site,{'a':rule}))
            self.assertIsNone(image_fingerprint(offer,site,{'a':{**rule,'permission_status':'unverified'}}))
    def test_description_supports_review_without_merging_and_expires(self):
        words=' '.join('caratteristica'+str(i) for i in range(25))
        a=self.row('a','Bunny Sogno Young Special',gtin='')
        b=self.row('b','Bunny Sogno Young Special Plus',gtin='')
        for row in (a,b):row['description_evidence']=description_evidence(words,row['url'],self.now.isoformat())
        result=self.model(a,b)
        self.assertEqual(result['metrics']['multi_shop_products'],0)
        self.assertEqual(len(result['matching_candidates']),1)
        self.assertIn('same_description',result['matching_candidates'][0]['reason'])
        b['description_evidence']['checked_at']=(self.now-dt.timedelta(days=31)).isoformat()
        self.assertNotIn('same_description',self.model(a,b)['matching_candidates'][0]['reason'])
