import copy
from pathlib import Path
import tempfile
import unittest
from check_matching_snapshot_contract import verify_models, files, explicit_resolver
from check_matching_merchant_review import verify

class MatchingContractTests(unittest.TestCase):
    def models(self):
        q={'verified':True,'weight_g':1000,'volume_ml':None,'pieces':None}
        base={'offers':[{'id':'a:1','merchant_id':'a','price':10,'affiliate_url':'https://a.example/x?a=1&b=2','gtin':'','quantity':q,'product_id':'old','canonical_title':'Before'},{'id':'b:1','merchant_id':'b','price':11,'affiliate_url':'https://b.example/x','gtin':'123','quantity':q,'product_id':'target','canonical_title':'Before'}],'products':[],'registry':{}}
        expected=copy.deepcopy(base);expected['offers'][0]['product_id']='target';expected['offers'][0]['canonical_title']='Expected'
        return base,copy.deepcopy(expected),expected,[['a:1','b:1']]
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
