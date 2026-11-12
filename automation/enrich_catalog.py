"""Bounded barcode enrichment from public product JSON; names select candidates only."""
import os,gzip,json,re,time,datetime,urllib.parse,urllib.robotparser,urllib.request
from pathlib import Path
try:
 from .update_catalog import get,UA,weight
except ImportError:
 from update_catalog import get,UA,weight
try:
 from .matching_evidence import description_evidence
except ImportError:
 from matching_evidence import description_evidence
ROOT=Path(__file__).resolve().parents[1]
def limited_get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=8) as r:return r.read()
def gtin(value):
 s=str(value or '').strip()
 if len(s) not in (8,12,13,14) or not s.isdigit() or len(set(s))==1:return ''
 check=(10-sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(s[:-1])) )%10)%10
 return s.zfill(14) if check==int(s[-1]) else ''
def eligible_for_identifier_lookup(o,brands):
 # A barcode identifies accessories, pieces and litres too. Shipping/net weight
 # is not a prerequisite for inspecting a variant, nor inferred from its barcode.
 return (o.get('source_type')!='official_feed' and
         o.get('merchant_id') in ('bauzaar','webpet','animaliapet') and
         o.get('available') is True and
         len(brands.get(o.get('brand','').casefold(),set()))>=2)

def lookup_priority(rows, score=0, priority_ids=frozenset()):
 # A page returns every variant. Inspect missing identifiers before refreshing
 # pages whose entire active selection already has valid barcodes.
 missing=sum(not gtin(o.get('gtin')) for o in rows)
 return (missing == 0, not any(o.get('id') in priority_ids for o in rows), -score, -missing)

def build():
 path=ROOT/'site/data/catalog.json.gz';d=json.loads(gzip.decompress(path.read_bytes()));cachepath=ROOT/'automation/identifier-cache.json'
 cache=json.loads(cachepath.read_text()) if cachepath.exists() else {};now=datetime.datetime.now(datetime.timezone.utc);robots={};urls={}
 # Recompute inferred title weights too: old parser results must not persist.
 from reviewed_identity import apply as apply_reviewed_identity
 from package_integrity import reconcile
 for o in d['offers']:
  reconcile(o)
 apply_reviewed_identity(d['offers'], json.loads((ROOT/'automation/reviewed-identities.json').read_text()), now)
 # Prefer matching brands and weights across sources, with both cats and dogs represented.
 brands={}
 for o in d['offers']:
  if o['available'] and o.get('brand'):brands.setdefault(o['brand'].casefold(),set()).add(o['merchant_id'])
 for o in d['offers']:
  if not eligible_for_identifier_lookup(o,brands):continue
  url=o['url'].split('?')[0]+'.js';key=o['id'];entry=cache.get(key)
  if entry and (now-datetime.datetime.fromisoformat(entry['checked_at'])).days<7:continue
  # Round robin merchants and species, not a claim of equivalence.
  cat='cat' if re.search(r'gatt|\bcat\b|kitten',o['title']+' '+o['category'],re.I) else 'dog'
  urls.setdefault((o['merchant_id'],cat),{})[url]=True
 # Approximate names only decide which pages to inspect first. GTIN still decides matches.
 buckets={};scores={}
 for o in d['offers']:
  if o.get('weight_kg'):buckets.setdefault((o['brand'].casefold(),o['weight_kg']),[]).append(o)
 for rows in buckets.values():
  if len({o['merchant_id'] for o in rows})<2:continue
  for a in rows:
   tokens=set(re.findall(r'[a-z]+',a['title'].casefold()))
   for b in rows:
    if a['merchant_id']==b['merchant_id']:continue
    other=set(re.findall(r'[a-z]+',b['title'].casefold()));score=len(tokens&other)/max(1,len(tokens|other));u=a['url'].split('?')[0]+'.js';scores[u]=max(scores.get(u,0),score)
 priority_path=ROOT/'site/data/priority-products.json'
 priority_ids=set(json.loads(priority_path.read_text()).get('priority_offer_ids',[])) if priority_path.exists() else set()
 page_rows={}
 for o in d['offers']:
  if o.get('available') is True:page_rows.setdefault(o['url'].split('?')[0]+'.js',[]).append(o)
 for key,group in urls.items():urls[key]=dict.fromkeys(sorted(group,key=lambda u:(*lookup_priority(page_rows.get(u,[]),scores.get(u,0),priority_ids),u)))
 selected=[];limit=max(0,min(60,int(os.environ.get("ENRICH_LIMIT","30"))))
 while len(selected)<limit and any(urls.values()):
  for group in urls.values():
   if group and len(selected)<limit:selected.append(next(iter(group)));group.pop(selected[-1])
 started=time.monotonic()
 for url in selected:
  if time.monotonic()-started>120:break
  base=urllib.parse.urlsplit(url);origin=base.scheme+'://'+base.netloc
  try:
   if origin not in robots:
    rp=urllib.robotparser.RobotFileParser();rp.parse(limited_get(origin+'/robots.txt').decode().splitlines());robots[origin]=rp
   if not robots[origin].can_fetch(UA,url):continue
   product=json.loads(limited_get(url))
   description=description_evidence(product.get('description',product.get('body_html','')),url,now.isoformat())
   mid=next(o['merchant_id'] for o in d['offers'] if o['url'].split('?')[0]+'.js'==url)
   for v in product.get('variants',[]):
    code=gtin(v.get('barcode'));cache[f'{mid}:{v["id"]}']={'gtin':code,'shipping_weight_kg':(v.get('weight') or 0)/1000 or None,'source':url,'checked_at':now.isoformat()}
   if description:
    for v in product.get('variants',[]):cache[f'{mid}:{v["id"]}']['description_evidence']=description
   cachepath.write_text(json.dumps(cache,separators=(',',':')))
   print('Identificativi letti:',mid,len(product.get('variants',[])),flush=True)
   time.sleep(.25)
  except Exception:continue
 for o in d['offers']:
  o['gtin']=gtin(o.get('gtin'));o['gtin_source']=o.get('gtin_source') or ('catalog' if o['gtin'] else '')
  e=cache.get(o['id'])
  if o.get('source_type')!='official_feed' and e and (now-datetime.datetime.fromisoformat(e['checked_at'])).days<30:
   if e.get('description_evidence'):o['description_evidence']={**e['description_evidence'],'retrieved_from':e['description_evidence']['source'],'source':o['url']}
   if e['gtin']:o.update(gtin=e['gtin'],gtin_source=e['source'],gtin_checked_at=e['checked_at'])
   if e.get('shipping_weight_kg'):o['shipping_weight_kg']=e['shipping_weight_kg']
 cachepath.write_text(json.dumps(cache,separators=(',',':')))
 path.write_bytes(gzip.compress(json.dumps(d,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
 groups={}
 for o in d['offers']:
  if o['gtin'] and o.get('weight_kg'):groups.setdefault((o['gtin'],o['weight_kg'],o['brand'].strip().casefold()),[]).append(o)
 matched=[v for v in groups.values() if len({o['merchant_id'] for o in v})>1]
 audit={'checked_at':now.isoformat(),'offers':len(d['offers']),'with_valid_gtin':sum(bool(o['gtin']) for o in d['offers']),'cross_shop_groups':len(matched),'method':'Codice a barre con checksum valido e stesso peso netto esplicito. Nomi non usati per certificare equivalenza.'}
 audit['reviewed_identities']=sum(bool(o.get('identity_review')) for o in d['offers'])
 audit['method']='GTIN con checksum valido e stesso peso netto; eventuali equivalenze revisionate riportano fonte e scadenza. Nessun abbinamento automatico per somiglianza del nome.'
 audit['merchant_coverage']={source['id']:{'offers':sum(o['merchant_id']==source['id'] for o in d['offers']),'with_gtin':sum(o['merchant_id']==source['id'] and bool(o.get('gtin')) for o in d['offers']),'with_weight':sum(o['merchant_id']==source['id'] and bool(o.get('weight_kg')) for o in d['offers']),'in_cross_shop_groups':sum(o['merchant_id']==source['id'] for g in matched for o in g)} for source in d['sources']}
 (ROOT/'site/data/catalog-quality.json').write_text(json.dumps(audit,ensure_ascii=False))
 print(json.dumps(audit));print('Requested product pages:',len(selected))
if __name__=='__main__':build()
