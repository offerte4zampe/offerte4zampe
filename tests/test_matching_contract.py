import copy
import datetime as dt
from pathlib import Path
import tempfile
import unittest
from check_matching_snapshot_contract import verify_models, files, explicit_resolver, hold_oracle, apply_expected_hold_metadata, verify_production_hold_manifest
from check_matching_merchant_review import verify,observation_fingerprint,verify_source_url

class MatchingContractTests(unittest.TestCase):
    def models(self):
        q={'verified':True,'weight_g':1000,'volume_ml':None,'pieces':None}
        base={'offers':[{'id':'a:1','merchant_id':'a','price':10,'affiliate_url':'https://a.example/x?a=1&b=2','gtin':'','quantity':q,'product_id':'old','canonical_title':'Before'},{'id':'b:1','merchant_id':'b','price':11,'affiliate_url':'https://b.example/x','gtin':'123','quantity':q,'product_id':'target','canonical_title':'Before'}],'products':[],'registry':{}}
        expected=copy.deepcopy(base);expected['offers'][0]['product_id']='target';expected['offers'][0]['canonical_title']='Expected'
        return base,copy.deepcopy(expected),expected,[['a:1','b:1']]
    def held_models(self):
        base,actual,expected,joins=self.models()
        row=copy.deepcopy(base['offers'][1]);row.update(id='c:1',merchant_id='c',product_id='target')
        base['offers'].append(copy.deepcopy(row));actual['offers'].append(copy.deepcopy(row));expected['offers'].append(copy.deepcopy(row))
        holds={'c:1':{'merchant_id':'c','review':{'review_state':'unverified','reason':'Independent manual commercial review pending','reviewed_at':'2026-11-20T08:00:00+00:00','review_due':'2026-11-27T08:00:00+00:00','sources':['https://c.example/exact']}}}
        for model in (actual,expected):
            model['offers'][2]['product_id']='held-c'
            model['metrics']={'name_matching':{}}
            apply_expected_hold_metadata(model,holds,dt.datetime(2026,11,20,12,tzinfo=dt.timezone.utc))
        return base,actual,expected,joins,holds

    def test_independent_join_and_review_hold_oracle_passes(self):
        result=verify_models(*self.held_models())
        self.assertEqual(result['exact_identity_moves'],2)

    def test_unknown_extra_hold_new_id_and_held_raw_mutation_are_rejected(self):
        for mode in ('extra_hold','extra_metadata','unknown_id','new_id','price','gtin','quantity','review_metadata','missing_hold'):
            base,actual,expected,joins,holds=self.held_models()
            if mode=='extra_hold':actual['offers'][1]['product_id']='extra-held-b'
            elif mode=='extra_metadata':actual['offers'][1]['comparison_review']={'review_state':'unverified'}
            elif mode=='unknown_id':holds['unknown:1']=copy.deepcopy(holds['c:1'])
            elif mode=='new_id':actual['offers'][2]['id']='new:1'
            elif mode=='review_metadata':actual['offers'][2]['comparison_review']['reason']='Unreviewed new metadata'
            elif mode=='missing_hold':actual['offers'][2]['product_id']='target'
            else:actual['offers'][2][mode]='changed raw field'
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify_models(base,actual,expected,joins,holds)

    def test_dormant_unknown_production_hold_and_changed_review_are_rejected(self):
        *_,holds=self.held_models()
        config={'schema_version':1,'holds':[{'offer_id':oid,'merchant_id':entry['merchant_id'],**entry['review']} for oid,entry in holds.items()]}
        verify_production_hold_manifest(config,holds)
        extra=copy.deepcopy(config);extra['holds'].append({**extra['holds'][0],'offer_id':'unknown:1','merchant_id':'unknown'})
        changed=copy.deepcopy(config);changed['holds'][0]['reason']='Not the independently reviewed reason'
        for invalid in (extra,changed):
            with self.assertRaises(AssertionError):verify_production_hold_manifest(invalid,holds)

    def test_independent_resolver_excludes_hold_from_original_resolution(self):
        seen=[]
        def original(offers,quantities,identities,*rest):
            seen.extend(o['id'] for o in offers)
            return identities,{},{}
        rows=[{'id':i,'merchant_id':i.split(':')[0]} for i in ('a:1','c:1')]
        holds={'c:1':{'merchant_id':'c','review':{}}}
        identities,_,_=explicit_resolver(original,[],holds)(rows,{}, {'a:1':['gtin','1'],'c:1':['gtin','1']},None,None,None)
        self.assertEqual(seen,['a:1']);self.assertEqual(identities['c:1'],['unattached','c:1'])

    def test_exact_explicit_move_passes(self):verify_models(*self.models())
    def test_commercial_and_derived_mutations_rejected(self):
        for key in ('price','affiliate_url','gtin','quantity','canonical_title','product_id'):
            with self.subTest(key=key):
                base,actual,expected,joins=self.models();actual['offers'][0][key]='changed'
                with self.assertRaises(AssertionError):verify_models(base,actual,expected,joins)
    def test_extra_move_missing_offer_and_new_indexable_rejected(self):
        for mode in ('extra','missing','indexable'):
            base,actual,expected,joins=self.models()
            if mode=='extra':actual['offers'][1]['product_id']='unexpected'
            elif mode=='missing':actual['offers'].pop()
            else:actual['products']=[{'id':'p','indexable':True,'verified_shop_count':1}]
            with self.assertRaises(AssertionError):verify_models(base,actual,expected,joins)
    def test_pending_merchant_review_is_rejected(self):
        with self.assertRaises(AssertionError):verify({'merchant_review':{'status':'pending'},'joins':[]})
    def test_status_alone_does_not_approve_join(self):
        with self.assertRaises(AssertionError):verify({'merchant_review':{'status':'verified','reviewer':'QA','evidence':[]},'joins':[['a','b']]})
    def test_html_sitemap_and_redirect_mutations_change_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'site/data').mkdir(parents=True)
            paths=('index.html','sitemap.xml','_redirects','data/canonical-sitemap.json','data/canonical-route-list.json')
            for p in paths:(root/'site'/p).write_text('baseline')
            baseline=files(root)
            for p in paths:
                (root/'site'/p).write_text('mutated');self.assertNotEqual(files(root),baseline)
                (root/'site'/p).write_text('baseline')

    def explicit_case(self,source_code,target_code,same_identity):
        offers=[{'id':'a','merchant_id':'a','brand':'Brand','gtin':source_code},{'id':'b','merchant_id':'b','brand':'Brand','gtin':target_code}]
        quantities={i:{'verified':True,'weight_g':1000,'volume_ml':None,'pieces':None} for i in ('a','b')}
        identities={'a':['same'] if same_identity else ['old'],'b':['same']}
        original=lambda offers,quantities,identities,*rest:(identities,{}, {})
        return explicit_resolver(original,[['a','b']])(offers,quantities,identities,str.lower,lambda x:x,lambda x:x or '')
    def test_equal_gtin_already_satisfied_is_no_op(self):
        identities,methods,_=self.explicit_case('123','123',True)
        self.assertEqual(identities,{'a':['same'],'b':['same']});self.assertEqual(methods,{})
    def test_conflicting_gtin_already_same_identity_rejected(self):
        with self.assertRaises(AssertionError):self.explicit_case('456','123',True)
    def test_missing_target_gtin_is_never_accepted(self):
        for same in (True,False):
            with self.assertRaises(AssertionError):self.explicit_case('','',same)
    def test_existing_valid_gtin_cannot_move_identity(self):
        for code in ('123','456'):
            with self.assertRaises(AssertionError):self.explicit_case(code,'123',False)

    def reviewed_case(self):
        now=dt.datetime.now(dt.timezone.utc)
        offers=[{'id':x+':1','title':'Brand Line Adult Pollo 1 kg','brand':'Brand','variant':'1 kg','url':'https://'+x+'.example/product','quantity':{'kind':'mass','value':1,'unit':'kg','weight_g':1000,'volume_ml':None,'pieces':None,'verified':True},'price':10,'available':True} for x in ('a','b')]
        sources=[{'offer_id':o['id'],'url':o['url'],'checked_at':now.isoformat(),'identity_observation_sha256':observation_fingerprint(o),'brand':'Brand','line':'Line','variant':'adult pollo','selling_quantity':'1 kg','evidence_excerpt':'Exact published selling unit and variant.'} for o in offers]
        manifest={'joins':[['a:1','b:1']],'merchant_review':{'status':'verified','reviewer':'Test review','evidence':[{'join':['a:1','b:1'],'result':'same_exact_product_and_selling_pack','sources':sources}]}}
        return manifest,{'offers':offers},now

    def test_review_binds_identity_but_not_live_price_or_stock(self):
        manifest,catalog,now=self.reviewed_case();verify(manifest,catalog,now)
        catalog['offers'][0].update(price=12,available=False)
        verify(manifest,catalog,now)

    def test_changed_reviewed_identity_is_rejected(self):
        for key in ('title','brand','variant','url','quantity'):
            manifest,catalog,now=self.reviewed_case()
            catalog['offers'][0][key]='changed' if key!='quantity' else {'kind':'mass','value':2,'unit':'kg','weight_g':2000,'verified':True}
            with self.subTest(key=key),self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def test_expired_future_or_misbound_review_is_rejected(self):
        for mode in ('expired','future','wrong_id','duplicate'):
            manifest,catalog,now=self.reviewed_case();s=manifest['merchant_review']['evidence'][0]['sources']
            if mode=='expired':s[0]['checked_at']=(now-dt.timedelta(days=30,seconds=1)).isoformat()
            elif mode=='future':s[0]['checked_at']=(now+dt.timedelta(seconds=1)).isoformat()
            elif mode=='wrong_id':s[0]['offer_id']='other:1'
            else:s[1]['offer_id']=s[0]['offer_id']
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def test_changed_gtin_feed_gtin_and_sku_invalidate_review(self):
        for key,value in [('gtin','8000500310427'),('feed_gtin','4006381333931'),('sku','changed-selected-sku')]:
            manifest,catalog,now=self.reviewed_case();catalog['offers'][0][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def test_gtin_padding_and_outer_sku_whitespace_are_equivalent(self):
        manifest,catalog,now=self.reviewed_case();row=catalog['offers'][0]
        row.update(gtin='3182550702263',feed_gtin='4006381333931',sku='FE1225FL')
        manifest['merchant_review']['evidence'][0]['sources'][0]['identity_observation_sha256']=observation_fingerprint(row)
        row.update(gtin='03182550702263',feed_gtin='04006381333931',sku=' FE1225FL ')
        verify(manifest,catalog,now)
        row['sku']='fe1225fl'
        with self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def test_malformed_gtin_values_do_not_collapse_to_missing(self):
        manifest,catalog,now=self.reviewed_case();row=catalog['offers'][0];row['gtin']='invalid-a'
        manifest['merchant_review']['evidence'][0]['sources'][0]['identity_observation_sha256']=observation_fingerprint(row)
        row['gtin']='invalid-b'
        with self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def test_unrelated_evidence_host_or_product_path_is_rejected(self):
        for url in ('https://unrelated.example/product','https://a.example/different-product'):
            manifest,catalog,now=self.reviewed_case();manifest['merchant_review']['evidence'][0]['sources'][0]['url']=url
            with self.subTest(url=url),self.assertRaises(AssertionError):verify(manifest,catalog,now)

    def shopify_url_case(self):
        offer={'id':'bauzaar:123','merchant_id':'bauzaar','url':'https://www.bauzaar.it/products/exact-product?variant=123'}
        source={'url':'https://www.bauzaar.it/products/exact-product.js','selected_id':'123'}
        return source,offer

    def test_shopify_api_and_selected_html_bind_exact_variant(self):
        source,offer=self.shopify_url_case();verify_source_url(source,offer)
        source['url']+='?variant=123';verify_source_url(source,offer)
        source['url']=offer['url'];verify_source_url(source,offer)

    def test_shopify_wrong_missing_duplicate_or_unrelated_variant_is_rejected(self):
        for mode in ('wrong_id','missing_id','query_other','query_duplicate','query_unknown','html_generic','selling_other'):
            source,offer=self.shopify_url_case()
            if mode=='wrong_id':source['selected_id']='999'
            elif mode=='missing_id':source.pop('selected_id')
            elif mode=='query_other':source['url']+='?variant=999'
            elif mode=='query_duplicate':source['url']+='?variant=123&variant=999'
            elif mode=='query_unknown':source['url']+='?variant=123&option=other'
            elif mode=='html_generic':source['url']='https://www.bauzaar.it/products/exact-product'
            else:offer['url']='https://www.bauzaar.it/products/exact-product?variant=999'
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify_source_url(source,offer)

    def test_isola_html_requires_exact_sku_path(self):
        offer={'id':'isola-dei-tesori:000123','merchant_id':'isola-dei-tesori','url':'https://www.isoladeitesori.it/prodotto/exact/000123.html'}
        source={'url':offer['url']};verify_source_url(source,offer)
        for url in ('https://www.isoladeitesori.it/prodotto/exact/000124.html',offer['url']+'?variant=other'):
            source['url']=url
            with self.assertRaises(AssertionError):verify_source_url(source,offer)
