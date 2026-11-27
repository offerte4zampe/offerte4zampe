import copy
import datetime as dt
import unittest
from check_matching_merchant_review import verify, observation_fingerprint, identity_snapshot_fingerprint


class MatchingDormantTests(unittest.TestCase):
    def fixture(self):
        now=dt.datetime(2026,11,27,12,tzinfo=dt.timezone.utc)
        def offer(merchant):
            return {'id':merchant+':1','merchant_id':merchant,'title':'Brand Line Adult Pollo 1 kg','brand':'Brand','variant':'1 kg','sku':'S1','url':'https://'+merchant+'.example/product','quantity':{'kind':'mass','value':1,'unit':'kg','weight_g':1000,'volume_ml':None,'pieces':None,'verified':True},'price':10,'available':True}
        rows={m:offer(m) for m in 'abcd'}
        def evidence(left,right):
            sources=[{'offer_id':o['id'],'url':o['url'],'checked_at':(now-dt.timedelta(days=4)).isoformat(),'source_sha256':'a'*64,'identity_observation_sha256':observation_fingerprint(o),'brand':'Brand','line':'Line','variant':'Adult Pollo','selling_quantity':'1kg','evidence_excerpt':'Exact SKU, line, recipe and complete selling pack reviewed.'} for o in [left,right]]
            return {'join':[left['id'],right['id']],'result':'same_exact_product_and_selling_pack','sources':sources}
        catalog={'generated_at':(now-dt.timedelta(hours=1)).isoformat(),'offers':[rows[m] for m in 'abd']}
        archive={'join':['c:1','d:1'],'missing_offer_ids':['c:1'],'reason':'Offer c:1 absent from this published input; upstream cause not established.','archived_at':now.isoformat(),'archived_reviewer':'Independent QA','input_snapshot':{'commit':'b'*40,'generated_at':catalog['generated_at'],'identity_snapshot_sha256':identity_snapshot_fingerprint(catalog)},'archived_review':evidence(rows['c'],rows['d'])}
        manifest={'schema_version':3,'joins':[['a:1','b:1']],'merchant_review':{'status':'verified','reviewer':'Independent QA','evidence':[evidence(rows['a'],rows['b'])]},'dormant_joins':[archive]}
        return manifest,catalog,rows,now

    def next_snapshot(self,catalog,now):
        catalog['generated_at']=(now+dt.timedelta(minutes=1)).isoformat()

    def test_explicit_absence_archived_without_mutating_inputs_or_active_gate(self):
        m,c,rows,now=self.fixture();saved=copy.deepcopy((m,c));plan=verify(m,c,now)
        self.assertEqual(plan['manifest']['joins'],[['a:1','b:1']])
        self.assertEqual(plan['dormant_states'][0]['state'],'dormant_absent')
        self.assertEqual((m,c),saved)
        c['offers'].pop(0)
        with self.assertRaises(AssertionError):verify(m,c,now)

    def test_new_and_present_pairs_keep_identity_and_expiry_checks(self):
        for mode in ['title','quantity','missing','expired']:
            m,c,rows,now=self.fixture();self.next_snapshot(c,now)
            if mode=='title':c['offers'][0]['title']='Different identity'
            elif mode=='quantity':c['offers'][0]['quantity']['weight_g']=2000
            elif mode=='missing':c['offers'].pop(0)
            else:m['merchant_review']['evidence'][0]['sources'][0]['checked_at']=(now-dt.timedelta(days=31)).isoformat()
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify(m,c,now)

    def test_returning_unchanged_pair_reactivates_only_with_current_valid_review(self):
        m,c,rows,now=self.fixture();self.next_snapshot(c,now);c['offers'].append(rows['c'])
        plan=verify(m,c,now)
        self.assertEqual(plan['manifest']['joins'],[['a:1','b:1'],['c:1','d:1']])
        self.assertEqual(plan['dormant_states'][0]['state'],'returned_unchanged_review_valid')

    def test_returned_changed_identity_fields_fail_closed(self):
        for field in ['title','brand','variant','url','sku','gtin','quantity']:
            m,c,rows,now=self.fixture();self.next_snapshot(c,now);c['offers'].append(rows['c'])
            rows['c'][field]={'kind':'mass','value':2,'unit':'kg','weight_g':2000,'verified':True} if field=='quantity' else 'changed'
            with self.subTest(field=field),self.assertRaises(AssertionError):verify(m,c,now)

    def test_remaining_counterpart_changes_or_absence_set_changes_are_not_silently_skipped(self):
        for mode in ['present_changed','both_missing','different_missing']:
            m,c,rows,now=self.fixture();self.next_snapshot(c,now)
            if mode=='present_changed':rows['d']['title']='Changed'
            elif mode=='both_missing':c['offers'].remove(rows['d'])
            else:c['offers'].remove(rows['d']);c['offers'].append(rows['c'])
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify(m,c,now)

    def test_expired_archive_is_history_while_absent_not_a_return_approval(self):
        m,c,rows,now=self.fixture();m['joins']=[];m['merchant_review']['evidence']=[]
        verify(m,c,now+dt.timedelta(days=31))
        self.next_snapshot(c,now);c['offers'].append(rows['c'])
        with self.assertRaises(AssertionError):verify(m,c,now+dt.timedelta(days=31))

    def test_price_stock_changes_do_not_invalidate_commercial_identity(self):
        m,c,rows,now=self.fixture();self.next_snapshot(c,now);c['offers'].append(rows['c']);rows['c'].update(price=12,available=False)
        verify(m,c,now)

    def test_incomplete_fabricated_future_or_duplicate_archives_fail(self):
        modes=['no_catalog','schema','reason','date','commit','digest','missing_ids','wrong_absence','source_digest','review_pair','reviewer','duplicate','overlap']
        for mode in modes:
            m,c,rows,now=self.fixture();e=m['dormant_joins'][0]
            if mode=='no_catalog':c=None
            elif mode=='schema':m['schema_version']=2
            elif mode=='reason':e['reason']=''
            elif mode=='date':e['archived_at']=(now+dt.timedelta(seconds=1)).isoformat()
            elif mode=='commit':e['input_snapshot']['commit']='bad'
            elif mode=='digest':e['input_snapshot']['identity_snapshot_sha256']='f'*64
            elif mode=='missing_ids':e['missing_offer_ids']=[]
            elif mode=='wrong_absence':e['missing_offer_ids']=['d:1']
            elif mode=='source_digest':e['archived_review']['sources'][0].pop('source_sha256')
            elif mode=='review_pair':e['archived_review']['join']=['x:1','d:1']
            elif mode=='reviewer':e['archived_reviewer']=''
            elif mode=='duplicate':m['dormant_joins'].append(copy.deepcopy(e))
            else:m['joins'].append(['d:1','c:1'])
            with self.subTest(mode=mode),self.assertRaises(AssertionError):verify(m,c,now)

if __name__=='__main__':unittest.main()
