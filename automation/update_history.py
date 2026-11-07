import os
"""Daily observed min/max prices; no backfill and no fabricated historical points."""
import gzip,json,datetime,hashlib,math,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def update(history,catalog,today):
 cutoff=(datetime.date.fromisoformat(today)-datetime.timedelta(days=179)).isoformat()
 rows=copy.deepcopy(history.get('offers',{}))
 identities=dict(history.get('identities',{}))
 for oid in list(rows):
  rows[oid]=[r for r in rows[oid] if r['day']>=cutoff]
  if not rows[oid]:del rows[oid]
 for o in catalog['offers']:
  # Failed imports retain old data: never invent an observation for the current day.
  if o['checked_at'][:10]!=today or not isinstance(o.get('price'),(int,float)) or not math.isfinite(o['price']) or o['price']<=0:continue
  fingerprint=hashlib.sha256(json.dumps([o.get(k) for k in ('merchant_id','title','variant','brand','gtin','weight_kg')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  # Establish a baseline for legacy rows; never join unidentified recipe/format history.
  if identities.get(o['id'])!=fingerprint:rows.pop(o['id'],None)
  identities[o['id']]=fingerprint
  items=rows.setdefault(o['id'],[]);previous=next((r for r in items if r['day']==today),None)
  if previous:
   previous.update(low=min(previous['low'],o['price']),high=max(previous['high'],o['price']),last=o['price'],available=o['available'],checked_at=o['checked_at'])
  else:items.append({'day':today,'low':o['price'],'high':o['price'],'last':o['price'],'available':o['available'],'checked_at':o['checked_at']})
 return {'started_at':history.get('started_at',today),'updated_at':catalog['generated_at'],'retention_days':180,'identities':{k:v for k,v in identities.items() if k in rows},'offers':rows}
def write_shards(history,directory):
 directory.mkdir(parents=True,exist_ok=True)
 buckets={format(n,'02x'):{} for n in range(256)}
 for oid,rows in history['offers'].items():
  buckets[hashlib.sha256(oid.encode()).hexdigest()[:2]][oid]=rows
 for prefix,offers in buckets.items():
  data={k:history[k] for k in ('started_at','updated_at','retention_days')}
  data['offers']=offers
  (directory/(prefix+'.json.gz')).write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))

def build():
 if os.environ.get('PRICE_TRACKING_ENABLED','false').lower() != 'true':
  print('Price history disabled; existing repository data left unchanged')
  return
 p=ROOT/'site/data/price-history.json.gz';old=json.loads(gzip.decompress(p.read_bytes())) if p.exists() else {}
 catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()));today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
 d=update(old,catalog,today);p.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0));write_shards(d,ROOT/'site/data/history');print('Observed history:',len(d['offers']),'offers since',d['started_at'])
if __name__=='__main__':build()
