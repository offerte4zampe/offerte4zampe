import unittest,importlib.util,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'automation'))
from enrich_catalog import gtin
from update_history import update,write_shards
class TrustTests(unittest.TestCase):
 def test_barcode_checksum(self):
  self.assertEqual(gtin('4006381333931'),'04006381333931')
  for code in ['4006381333932','not-a-code','0000000000000','123']:self.assertEqual(gtin(code),'')
 def test_real_daily_range_no_duplicate_or_stale_backfill(self):
  o={'id':'bauzaar:a','merchant_id':'bauzaar','price':10,'available':True,'checked_at':'2026-10-18T08:00:00Z'}
  cat={'generated_at':'2026-10-18T08:00:00Z','offers':[o]}
  h=update({},cat,'2026-10-18');o['price']=12;h=update(h,cat,'2026-10-18');self.assertEqual(len(h['offers']['bauzaar:a'),1);self.assertEqual(h['offers']['bauzaar:a'[0]['low'],10);self.assertEqual(h['offers']['bauzaar:a'[0]['high'],12)
  h=update(h,cat,'2026-10-19');self.assertEqual(len(h['offers']['bauzaar:a'),1)
 def test_retention_identity_changes_and_legacy_baseline(self):
  o={'id':'bauzaar:a','merchant_id':'bauzaar','title':'Ricetta A','variant':'10 kg','price':10,'available':True,'checked_at':'2026-10-18T08:00:00Z'}
  cat={'generated_at':o['checked_at'],'offers':[o]}
  h=update({},cat,'2026-10-18');self.assertEqual(h['retention_days'],180)
  o.update(title='Ricetta B',price=20,checked_at='2026-10-19T08:00:00Z');h=update(h,cat,'2026-10-19')
  self.assertEqual([r['day'] for r in h['offers']['bauzaar:a'],['2026-10-19'])
  old={'offers':{'bauzaar:a':[{'day':'2026-10-17','low':1,'high':1}]}}
  self.assertEqual(len(update(old,cat,'2026-10-19')['offers']['bauzaar:a'),1)
  h=update(h,{'generated_at':'2027-05-01T00:00:00Z','offers':[]},'2027-05-01');self.assertEqual(h['offers'],{})
 def test_invalid_prices_never_enter_observations(self):
  for price in [0,-1,float('nan'),float('inf')]:
   h=update({}, {'generated_at':'2026-10-20T08:00:00Z','offers':[{'id':'bauzaar:a','merchant_id':'bauzaar','price':price,'checked_at':'2026-10-20T08:00:00Z'}]},'2026-10-20')
   self.assertEqual(h['offers'],{})

 def test_shards_are_complete_and_exclude_private_identity_map(self):
  import tempfile,gzip,json,hashlib
  history={'started_at':'2026-10-20','updated_at':'2026-10-20T08:00:00Z','retention_days':180,'identities':{'a':'hash'},'offers':{'bauzaar:a':[{'day':'2026-10-20','low':10,'high':10}]}}
  with tempfile.TemporaryDirectory() as directory:
   write_shards(history,Path(directory));self.assertEqual(len(list(Path(directory).glob('*.gz'))),256)
   shard=json.loads(gzip.decompress((Path(directory)/(hashlib.sha256(b'a').hexdigest()[:2]+'.json.gz')).read_bytes()))
   self.assertEqual(shard['offers'],history['offers']);self.assertNotIn('identities',shard)
