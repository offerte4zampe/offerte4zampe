import unittest,sys,json,html,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation'))
from paco_feed import normalize,verify_quantity,verification_plan
import datetime as dt
def fixture():
 return {'products':[{'ID':'123','campaignID':24833,'name':'Test cibo','price':{'currency':'EUR','amount':24},'URL':'https://www.pacopetshop.it/directlinking/?tt=24833_1216771_518044_&r=https%3A%2F%2Fwww.pacopetshop.it%2Fit%2Fbrand%2F123-test.htm','properties':{'availability':['out of stock'],'sale_price':['20.00 EUR'],'GTIN':['4006381333931'],'brand':['Brand']},'variations':[]}]}
class PacoFeedTest(unittest.TestCase):
 def test_feed_stock_tracking_price_without_unit_inference(self):
  r=normalize(fixture())[0];self.assertEqual(r['price'],20);self.assertFalse(r['available']);self.assertEqual(r['gtin'],'');self.assertIsNone(r['weight_kg']);self.assertIn('tt=24833_',r['affiliate_url']);self.assertIsNone(r['previous_price']);self.assertEqual(r['merchant_promotion']['reference_cents'],2400)
 def test_verified_multipack_and_mismatch(self):
  r=normalize(fixture())[0];p={'id':123,'price_amount':20,'attributes':{'1':{'name':'Pollo','ean13':'4006381333931'},'2':{'name':'24x85 gr','ean13':'4006381333931'}}}
  page=lambda:'<div data-product="'+html.escape(json.dumps(p),quote=True)+'">'
  v=verify_quantity(r,page());self.assertEqual(v['weight_kg'],2.04);self.assertTrue(v['quantity_verified'])
  p['price_amount']=21;self.assertFalse(verify_quantity(r,page())['quantity_verified'])
  p['price_amount']=20;p['attributes']['1']['ean13']='other';self.assertFalse(verify_quantity(r,page())['quantity_verified'])
 def test_reject_foreign_tracking_or_destination_and_duplicates(self):
  for replacement in ['tt=999_','r=https%3A%2F%2Fevil.example%2F']:
   f=fixture();f['products'][0]['URL']=f['products'][0]['URL'].replace('tt=24833_',replacement) if replacement.startswith('tt') else f['products'][0]['URL'].split('&r=')[0]+'&'+replacement
   with self.assertRaises(ValueError):normalize(f)
  f=fixture();f['products']*=2
  with self.assertRaises(ValueError):normalize(f)
 def test_invalid_price_not_published(self):
  f=fixture();f['products'][0]['price']['amount']=0
  with self.assertRaises(ValueError):normalize(f)
if __name__=='__main__':unittest.main()

class PacoVerificationPlanTest(unittest.TestCase):
 def setUp(self):
  self.now=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)
 def test_budget_rotates_past_first_forty_and_failed_attempts(self):
  rows=[dict(normalize(fixture())[0],id='paco:'+str(i)) for i in range(80)]
  chosen=verification_plan(rows,[],{'4006381333931'},self.now,limit=40)
  self.assertEqual(len(chosen),40)
  old=copy.deepcopy(rows)
  for i in chosen: old[i]['quantity_verification_attempted_at']=self.now.isoformat()
  following=verification_plan(copy.deepcopy(rows),old,{'4006381333931'},self.now+dt.timedelta(hours=6),limit=40)
  self.assertEqual(len(following),40);self.assertFalse(set(chosen)&set(following))
 def verified(self):
  row=normalize(fixture(),self.now)[0]
  p={'id':123,'price_amount':20,'attributes':{'1':{'name':'24x85 gr','ean13':row['feed_gtin']}}}
  return verify_quantity(row,'<div data-product="'+html.escape(json.dumps(p),quote=True)+'">',self.now)
 def test_recent_exact_proof_reused_without_resetting_evidence_date(self):
  prior=self.verified();rows=normalize(fixture(),self.now+dt.timedelta(hours=6))
  self.assertEqual(verification_plan(rows,[prior],set(),self.now+dt.timedelta(hours=6)),[])
  self.assertEqual(rows[0]['weight_kg'],2.04);self.assertEqual(rows[0]['quantity_checked_at'],prior['quantity_checked_at'])
 def test_expired_future_or_changed_evidence_requires_new_verification(self):
  for change in [{'price':19},{'feed_gtin':'other'},{'url':'https://example.com'},{'title':'Changed'}]:
   rows=normalize(fixture(),self.now);rows[0].update(change)
   self.assertEqual(verification_plan(rows,[self.verified()],set(),self.now),[0])
  for age in [dt.timedelta(hours=37),dt.timedelta(hours=-1)]:
   rows=normalize(fixture(),self.now)
   self.assertEqual(verification_plan(rows,[self.verified()],set(),self.now+age),[0])
 def test_peer_candidates_precede_nonmatching_candidates(self):
  a=normalize(fixture(),self.now)[0];b=dict(a,id='paco:9',feed_gtin='other')
  self.assertEqual(verification_plan([b,a],[],{a['feed_gtin']},self.now,limit=1),[1])


 def test_brand_typography_does_not_reset_quantity_proof(self):
  prior=self.verified();prior['brand']='KONG'
  rows=normalize(fixture(),self.now);rows[0]['brand']='Kong'
  self.assertEqual(verification_plan(rows,[prior],set(),self.now),[])
  self.assertEqual(rows[0]['quantity_checked_at'],prior['quantity_checked_at'])
  rows=normalize(fixture(),self.now);rows[0]['brand']='Farmina'
  self.assertEqual(verification_plan(rows,[prior],set(),self.now),[0])

 def test_catalog_padded_gtin_preserves_quantity_proof_across_refresh(self):
  prior=self.verified();prior['gtin']=prior['gtin'].zfill(14)
  rows=normalize(fixture(),self.now+dt.timedelta(hours=6))
  self.assertEqual(verification_plan(rows,[prior],set(),self.now+dt.timedelta(hours=6)),[])
  self.assertTrue(rows[0]['quantity_verified']);self.assertEqual(rows[0]['weight_kg'],2.04)
  self.assertEqual(rows[0]['quantity_checked_at'],prior['quantity_checked_at'])

 def test_available_candidates_precede_sold_out_peer_matches(self):
  a=normalize(fixture(),self.now)[0]
  b=dict(a,id='paco:9',available=True)
  self.assertEqual(verification_plan([a,b],[],{a['feed_gtin']},self.now,limit=1),[1])

 def test_available_cohort_offer_precedes_other_peer_without_bypassing_stock(self):
  a=normalize(fixture(),self.now)[0];a['available']=True
  b=dict(a,id='paco:9')
  self.assertEqual(verification_plan([a,b],[],{a['feed_gtin']},self.now,limit=1,priority_ids={'paco:9'}),[1])
  b['available']=False
  self.assertEqual(verification_plan([a,b],[],{a['feed_gtin']},self.now,limit=1,priority_ids={'paco:9'}),[0])

 def test_recent_failed_priority_cohort_cannot_starve_unattempted_peer(self):
  failed=dict(normalize(fixture(),self.now)[0],id='paco:priority',available=True)
  other=dict(failed,id='paco:new')
  prior=dict(failed,quantity_verification_attempted_at=(self.now-dt.timedelta(hours=6)).isoformat())
  rows=[copy.deepcopy(failed),other]
  self.assertEqual(verification_plan(rows,[prior],{failed['feed_gtin']},self.now,limit=1,priority_ids={failed['id']}),[1])
  self.assertFalse(rows[0]['quantity_verified']);self.assertFalse(rows[1]['quantity_verified'])
  self.assertEqual(rows[0]['gtin'],'');self.assertEqual(rows[1]['gtin'],'')

 def test_recent_attempt_is_fallback_not_a_ban_and_stock_still_wins(self):
  a=dict(normalize(fixture(),self.now)[0],available=True)
  prior=dict(a,quantity_verification_attempted_at=(self.now-dt.timedelta(hours=6)).isoformat())
  sold_out=dict(a,id='paco:sold-out',available=False)
  self.assertEqual(verification_plan([copy.deepcopy(a),sold_out],[prior],{a['feed_gtin']},self.now,limit=1),[0])
  self.assertEqual(verification_plan([copy.deepcopy(a)],[prior],set(),self.now,limit=1),[0])

 def test_retry_priority_returns_at24h_and_changed_fingerprint_resets_attempt(self):
  a=dict(normalize(fixture(),self.now)[0],id='paco:priority',available=True)
  b=dict(a,id='paco:new')
  for age,expected in [(dt.timedelta(hours=24)-dt.timedelta(microseconds=1),[1]),(dt.timedelta(hours=24),[0])]:
   prior=dict(a,quantity_verification_attempted_at=(self.now-age).isoformat())
   self.assertEqual(verification_plan([copy.deepcopy(a),copy.deepcopy(b)],[prior],{a['feed_gtin']},self.now,limit=1,priority_ids={a['id']}),expected)
  for change in [{'price':a['price']+1},{'title':'Different product'},{'feed_gtin':'other'},{'url':a['url']+'?changed=1'}]:
   prior=dict(a,quantity_verification_attempted_at=(self.now-dt.timedelta(hours=6)).isoformat(),**change)
   self.assertEqual(verification_plan([copy.deepcopy(a),copy.deepcopy(b)],[prior],{a['feed_gtin']},self.now,limit=1,priority_ids={a['id']}),[0])

class PacoSelectedProductIdentityTest(unittest.TestCase):
 def test_wrong_missing_or_conflicting_product_id_never_proves_a_pack(self):
  row=normalize(fixture())[0]
  base={'id':123,'id_product':123,'id_product_attribute':5189,'price_amount':20,'attributes':{'7':{'name':'24x85 gr','ean13':row['feed_gtin']}}}
  def verify(payload,diagnostics=None):
   return verify_quantity(row,'<div data-product="'+html.escape(json.dumps(payload),quote=True)+'">',diagnostics=diagnostics)
  self.assertTrue(verify(base)['quantity_verified'])
  for patch in [{'id':999,'id_product':999},{'id':None},{'id':True},{'id_product':999}]:
   diagnostics={};result=verify({**base,**patch},diagnostics)
   self.assertFalse(result['quantity_verified']);self.assertEqual(result,row)
   self.assertEqual(diagnostics['reason'],'product_id_mismatch')
  missing=dict(base);missing.pop('id');self.assertFalse(verify(missing)['quantity_verified'])
