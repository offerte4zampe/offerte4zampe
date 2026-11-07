"""Merchant evidence diagnostics are non-authoritative and offline only."""
import copy
import datetime as dt
import html
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automation.merchant_evidence import (
    CATEGORIES, PATH, bauzaar_report, classify_gtin,
    paco_record, save_section, signature)
from automation.paco_feed import verify_quantity


class PrivateMerchantEvidenceTests(unittest.TestCase):
    def test_classification_is_exclusive_without_normalizing_identifiers(self):
        samples = {
            'spaces': '400638 1333931',
            'separators': '400638-1333931',
            'non_numeric': '400638A333931',
            'leading_zeros': '0004006381333931',
            'length': '123456789',
            'checksum': '4006381333932',
        }
        self.assertEqual(set(samples),set(CATEGORIES))
        rows=[{'id':'bauzaar:'+str(i),'feed_gtin':v}
              for i,v in enumerate(samples.values())]
        original=copy.deepcopy(rows)
        self.assertIsNone(classify_gtin('4006381333931'))
        for kind,value in samples.items():
            self.assertEqual(classify_gtin(value),kind)
        report=bauzaar_report(rows)
        self.assertEqual(report['invalid_total'],len(samples))
        self.assertEqual(report['counts'],dict.fromkeys(CATEGORIES,1))
        self.assertTrue(all(len(report['examples'][k])==1 for k in samples))
        self.assertEqual(rows,original)
        self.assertEqual(len(bauzaar_report([rows[0]]*12)['examples']['spaces']),10)

    def test_record_allowlist_fingerprint_and_no_mutation(self):
        now=dt.datetime(2026,11,7,12,tzinfo=dt.timezone.utc)
        row={'id':'paco:123','feed_gtin':'4006381333931','sku':'ABC',
             'title':'Confezione 24 x 85 g','price':27.50,
             'affiliate_url':'https://secret.invalid/?token=PRIVATE'}
        before=copy.deepcopy(row)
        context={'page_ean13':['4006381333932'],
                 'page_variant_id':['23'],
                 'page_variant_label':['24 x 85 gr']}
        mismatch=paco_record(row,'ean_mismatch',now,context)
        self.assertEqual(mismatch['page_ean13'],['4006381333932'])
        self.assertEqual(mismatch['feed_sku'],'ABC')
        self.assertEqual(mismatch['page_variant_id'],['23'])
        self.assertEqual(mismatch['failure_reason'],'ean_mismatch')
        self.assertNotIn('price',mismatch)
        self.assertNotIn('affiliate_url',json.dumps(mismatch))
        verified={**row,'gtin':row['feed_gtin'],'quantity_verified':True,
                  'weight_kg':2.04}
        success=paco_record(row,None,now,context,verified)
        self.assertRegex(success['identity_fingerprint'],r'^[a-f0-9]{64}$')
        self.assertNotEqual(success['identity_fingerprint'],
                            signature({'sku':'ABC','ean':row['feed_gtin'],
                                       'title':row['title'],'weight_kg':1.02}))
        self.assertEqual(row,before)

    def test_page_context_never_changes_verification_result(self):
        now=dt.datetime(2026,11,7,12,tzinfo=dt.timezone.utc)
        row={'id':'paco:123','feed_gtin':'4006381333931','sku':'S1',
             'title':'Test','price':20,'quantity_verified':False}
        payload={'price_amount':20,
                 'attributes':{'variant-1':{'ean13':'4006381333932',
                                            'name':'24x85 gr'}}}
        page='<div data-product="'+html.escape(json.dumps(payload),quote=True)+'">'
        blank=verify_quantity(row,page,now=now)
        captured={}
        observed=verify_quantity(row,page,now=now,diagnostics=captured)
        self.assertEqual(blank,observed)
        self.assertEqual(captured['reason'],'ean_mismatch')
        self.assertEqual(captured['page_ean13'],['4006381333932'])
        self.assertEqual(captured['page_variant_id'],['variant-1'])
        self.assertEqual(captured['page_variant_label'],['24x85 gr'])

    def test_private_atomic_file_and_failing_writes_are_nonblocking(self):
        self.assertFalse(str(PATH).find('/site/data/')>=0)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'private'/'latest.json'
            self.assertTrue(save_section('bauzaar',{'counts':{'checksum':3}},target))
            self.assertTrue(save_section('paco',{'records':[{'offer_id':'paco:1'}]},target))
            stored=json.loads(target.read_text())
            self.assertEqual(set(stored),{'bauzaar','paco'})
            self.assertFalse(save_section('paco',{},Path(tmp)/'private'))
            self.assertEqual(json.loads(target.read_text()),stored)

if __name__=='__main__':
    unittest.main()
