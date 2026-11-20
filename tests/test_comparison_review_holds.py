import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from automation.build_product_catalog import build
from automation.comparison_review import MANIFEST, review_holds, validate_manifest


class ComparisonReviewTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,20,12,tzinfo=dt.timezone.utc)
        self.empty={'schema_version':1,'holds':[]}
        self.manifest=json.loads(MANIFEST.read_text())
        def offer(oid,brand,title,gtin):
            merchant=oid.split(':')[0]
            return dict(id=oid,merchant_id=merchant,merchant=merchant,brand=brand,title=title,variant='',gtin=gtin,
                        price=18.9,available=True,checked_at=self.now.isoformat(),url='https://'+merchant+'.example/item',
                        affiliate_url='https://affiliate.example/?id='+oid,image='')
        self.rows=[offer('bauzaar:56961508409669','PetUp','PetUp Guinzaglio nero','8032611677953'),
                   offer('isola-dei-tesori:000154414','PetUp','PetUp Guinzaglio nero','8032611677953'),
                   offer('webpet:52569197674836','Askoll','Askoll Robofood mangiatoia','8050683000387'),
                   offer('isola-dei-tesori:000166136','Askoll','Askoll Robofood mangiatoia','8050683000387'),
                   offer('bauzaar:99','Other','Other accessorio','4006381333931'),
                   offer('webpet:99','Other','Other accessorio','4006381333931')]
        self.catalog={'offers':self.rows,'generated_at':self.now.isoformat()}

    def test_only_two_reviewed_rows_split_comparisons_without_mutating_inputs(self):
        before=build(self.catalog,now=self.now,comparison_reviews=self.empty)
        frozen=copy.deepcopy(self.catalog)
        after=build(self.catalog,before['registry'],now=self.now,comparison_reviews=self.manifest)
        self.assertEqual(self.catalog,frozen)
        a={o['id']:o for o in after['offers']};b={o['id']:o for o in before['offers']}
        self.assertEqual(set(a),set(b))
        held={'bauzaar:56961508409669','webpet:52569197674836'}
        self.assertEqual({i for i,o in a.items() if 'comparison_review' in o},held)
        for oid,o in a.items():
            for key in self.rows[0]:self.assertEqual(o.get(key),b[oid].get(key),(oid,key))
        for oid in held:
            self.assertEqual(a[oid]['offer_matching_method'],'comparison_review_hold')
            self.assertFalse(a[oid]['product_identity_verified'])
            product=next(p for p in after['products'] if p['id']==a[oid]['product_id'])
            self.assertEqual(product['offer_ids'],[oid]);self.assertFalse(product['indexable'])
        old_other=next(p for p in before['products'] if 'bauzaar:99' in p['offer_ids'])
        new_other=next(p for p in after['products'] if 'bauzaar:99' in p['offer_ids'])
        self.assertEqual(old_other,new_other)
        self.assertEqual(before['metrics']['multi_shop_products']-after['metrics']['multi_shop_products'],2)

    def test_explicit_release_clears_derived_metadata_and_allows_exact_join(self):
        held=build(self.catalog,now=self.now,comparison_reviews=self.manifest)
        released=build({'offers':held['offers'],'generated_at':self.now.isoformat()},held['registry'],now=self.now,comparison_reviews=self.empty)
        self.assertFalse(any('comparison_review' in o for o in released['offers']))
        self.assertEqual(released['metrics']['multi_shop_products'],3)

    def test_due_review_and_changed_price_never_release_a_hold(self):
        later=self.now+dt.timedelta(days=90)
        rows=copy.deepcopy(self.rows);rows[0]['price']=99
        held=review_holds(rows,later,self.manifest)
        self.assertEqual(set(held),{'bauzaar:56961508409669','webpet:52569197674836'})
        self.assertTrue(all(h['review_due_reached'] for h in held.values()))
        released=review_holds(rows,later,self.empty)
        self.assertEqual(released,{})  # Explicit reviewed manifest removal, never timer expiry.

    def test_name_resolver_cannot_reattach_a_held_row(self):
        rows=copy.deepcopy(self.rows[:2])
        rows[0].update(gtin='',title='Brand Super Premium Adult Pollo 2 kg',weight_kg=2,brand='Brand')
        rows[1].update(title='Brand Super Premium Adult Pollo 2 kg',weight_kg=2,brand='Brand')
        without=build({'offers':rows,'generated_at':self.now.isoformat()},now=self.now,comparison_reviews=self.empty)
        with_hold=build({'offers':rows,'generated_at':self.now.isoformat()},now=self.now,comparison_reviews=self.manifest)
        self.assertEqual(without['metrics']['multi_shop_products'],1)
        self.assertEqual(with_hold['metrics']['multi_shop_products'],0)

    def test_malformed_configuration_aborts_instead_of_enabling_joins(self):
        invalid=[{'schema_version':True,'holds':[]},{}, {'schema_version':1,'holds':{}}, {'schema_version':1,'holds':[{}]}]
        for change in ({'review_state':'verified'},{'merchant_id':'amazon'},{'offer_id':'bauzaar:wrong space'},
                       {'sources':[]},{'reviewed_at':'2026-11-20'},{'review_due':'2020-01-01T00:00:00Z'}):
            doc=copy.deepcopy(self.manifest);doc['holds'][0].update(change);invalid.append(doc)
        duplicate=copy.deepcopy(self.manifest);duplicate['holds'].append(duplicate['holds'][0]);invalid.append(duplicate)
        for doc in invalid:
            with self.subTest(doc=doc),self.assertRaises(ValueError):build(self.catalog,now=self.now,comparison_reviews=doc)
        with patch.object(Path,'read_text',side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):review_holds(self.rows,self.now)

    def test_exact_offer_and_merchant_binding(self):
        other=copy.deepcopy(self.rows);other[0]['id']='bauzaar:569615084096690'
        self.assertNotIn(other[0]['id'],review_holds(other,self.now,self.manifest))
        other=copy.deepcopy(self.rows);other[0]['merchant_id']='webpet'
        with self.assertRaises(ValueError):review_holds(other,self.now,self.manifest)


if __name__=='__main__':unittest.main()
