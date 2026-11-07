"""Import public merchant catalogs; use approved official feeds where available; never invent prices."""
import gzip
import concurrent.futures, datetime, json, os, re, time, urllib.request, urllib.robotparser
from decimal import Decimal, InvalidOperation
from pathlib import Path
try:
    from .gtin_diagnostics import gtin_counters
except ImportError:
    from gtin_diagnostics import gtin_counters
try:
    from .freshness import source_freshness
except ImportError:
    from freshness import source_freshness
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('bauzaar','Bauzaar','https://www.bauzaar.it'),('webpet','WebPet','https://www.webpet.it'),('animaliapet','Animaliapet','https://www.animaliapet.eu'),('isola-dei-tesori','Isola dei Tesori','https://www.isoladeitesori.it'),('paco','Paco Pet Shop','https://www.pacopetshop.it'),('hygge','Hygge Pet Food','https://hyggepetfood.com')]
UA='Offerte a 4 ZampeCatalog/1.0 (+https://offerte4zampe.it/contatti.html)'
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/plain'})
    with urllib.request.urlopen(req,timeout=35) as r:
        if r.status!=200: raise ValueError('HTTP '+str(r.status))
        return r.read()
def amount(v):
    try:
        d=Decimal(str(v)); return float(d) if d.is_finite() and 0<d<100000 else None
    except (InvalidOperation,ValueError): return None
def weight(label):
    """Net weight of the selling pack, only from explicit unambiguous quantities."""
    s=str(label or '').lower().replace(',', '.')
    s=re.sub(r'(?<=\d)\s*gr\b|\bgr\b', 'g', s)
    s=re.sub(r'\b(adult|senior|ageing|mature|maxi|medium|mini)\s+\d{1,2}\+(?!\d)', r'\1', s)
    if '+' in s or re.search(r'\d\s*[-–/]\s*\d|\b(?:peso del cane|peso corporeo|cani da|fino a|oltre)\b',s): return None
    number=r'(\d+(?:\.\d+)?)'
    unit=r'(kg|g)(?=\b|[x×]\d)'
    count=r'(?:pz|pezzi|lattine|buste|bustine|compresse|confezioni|stick)'
    # Count before unit (30 pz x 1 g) and reverse (1 g x 30).
    patterns=[(r'(?<![\d.])(\d+)\s*(?:'+count+r'\s*)?[x×]\s*'+number+r'\s*'+unit, False),
              (r'(?<![\d.])'+number+r'\s*'+unit+r'\s*[x×]\s*(\d+)(?![\d.])\s*(?:'+count+r'\b)?', True),
              (r'(?<![\d.])(\d+)\s*'+count+r'\s+da\s+'+number+r'\s*'+unit, False)]
    # Feed titles explicitly describe the selling multipack after the unit name.
    selling=re.search(r'\bconfezione\s+da\s+(\d+)\s*(?:pezzi|pz|lattine|buste|bustine)\b',s)
    if selling:
        remainder=s[:selling.start()]+s[selling.end():]
        measures=list(re.finditer(r'(?<![\d.])'+number+r'\s*'+unit,remainder))
        values={round(float(m[1])/(1000 if m[2]=='g' else 1),6) for m in measures}
        if len(values)!=1 or re.search(r'\d+\s*[x×]|[x×]\s*\d|\d+\s*'+count+r'\b',remainder):return None
        total=round(int(selling[1])*next(iter(values)),6)
        return total if 0<total<=1000 else None
    packs=[]
    for pattern,reverse in patterns:
        for m in re.finditer(pattern,s):
            n,amount,u=(int(m[3]),float(m[1]),m[2]) if reverse else (int(m[1]),float(m[2]),m[3])
            # Additional quantities outside this explicit pack make the label ambiguous.
            remainder=s[:m.start()]+s[m.end():]
            if re.search(number+r'\s*'+unit,remainder) or re.search(r'\d+\s*'+count+r'\b',remainder): return None
            total=round(n*amount/(1000 if u=='g' else 1),6)
            if n>0 and 0<total<=1000:packs.append(total)
    if packs:return packs[0] if len(packs)==1 else None
    if re.search(r'\d+\s*'+count+r'\b|(?<![a-z])[x×]\s*\d',s): return None
    matches=list(re.finditer(r'(?<![\d.])'+number+r'\s*'+unit,s))
    if len(matches)==1:
        kg=float(matches[0][1])/(1000 if matches[0][2]=='g' else 1)
        return kg if 0<kg<=1000 else None
    return None

def collect(source, shipping_only=False):
    sid,name,base=source; now=datetime.datetime.now(datetime.timezone.utc).isoformat(); rows=[]
    try:
        if sid=='hygge':
            try:
                from .hygge_awin_feed import collect as hygge_collect
            except ImportError:
                from hygge_awin_feed import collect as hygge_collect
            return hygge_collect()
        if sid=='paco':
            from paco_feed import collect as paco_collect
            return paco_collect()
        if sid=='isola-dei-tesori':
            from isola_feed import collect as isola_collect
            return isola_collect()
        if sid=='bauzaar' and not shipping_only:
            from bauzaar_feed import collect as official_collect
            from shipping_metadata import supplement
            rows,status=official_collect()
            supplement(rows,lambda:collect(source,True),ROOT/'automation/shipping-cache.json')
            return rows,status
        rp=urllib.robotparser.RobotFileParser();rp.parse(get(base+'/robots.txt').decode().splitlines())
        if not rp.can_fetch(UA,base+'/products.json'):raise ValueError('Catalog access disallowed by robots')
        seen=set(); complete=False
        for page in range(1,101):
            products=json.loads(get(f'{base}/products.json?limit=250&page={page}'))['products']
            if not products:complete=True;break
            for p in products:
                if str(p['id']) in seen: raise ValueError('Repeated pagination')
                seen.add(str(p['id']))
                for v in p.get('variants',[]):
                    price=amount(v.get('price'))
                    if not price:continue
                    variant=v.get('title',''); variant='' if variant=='Default Title' else variant
                    title=str(p['title']);kg=weight(variant) if re.search(r'\d\s*(?:kg|g)\b',variant.lower()) else weight(title)
                    before=amount(v.get('compare_at_price'))
                    rows.append({'id':f'{sid}:{v["id"]}','merchant':name,'merchant_id':sid,'title':title,'variant':variant,'brand':p.get('vendor',''),'category':p.get('product_type',''),'price':price,'previous_price':before if before and before>price else None,'available':bool(v.get('available')),'url':base+'/products/'+p['handle']+'?variant='+str(v['id']),'image':(p.get('images') or [{}])[0].get('src',''),'sku':str(v.get('sku') or ''),'gtin':str(v.get('barcode') or ''),'feed_gtin':str(v.get('barcode') or ''),'weight_kg':kg,'shipping_weight_kg':(amount(v.get('grams'))/1000 if amount(v.get('grams')) else None),'checked_at':now})
            if len(products)<250:complete=True;break
            time.sleep(.3)
        if not complete:raise ValueError('Catalog exceeded pagination safety limit')
        return rows,{'id':sid,'name':name,'status':'ok','checked_at':now,'offers':len(rows),'source':base+'/products.json','method':'Catalogo pubblico del negozio'}
    except Exception as e:
        return [],{'id':sid,'name':name,'status':'error','checked_at':now,'offers':0,'error':type(e).__name__,'source':base+'/products.json'}
def main():
    path=ROOT/'site/data/catalog.json';old=json.loads(gzip.decompress(path.with_suffix('.json.gz').read_bytes())) if path.with_suffix('.json.gz').exists() else {'offers':[]}
    offers=[];sources=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for rows,status in pool.map(collect,SOURCES):
            if status['status']=='error':
                rows=[r for r in old.get('offers',[]) if r['merchant_id']==status['id']];status['offers']=len(rows);status['status']='stale' if rows else 'error'
            # Diagnostics are metadata only; do not mutate offer records.
            try:
                status['gtin_diagnostics'] = gtin_counters(rows)
            except Exception as error:
                # Diagnostics must never stop a catalog refresh.
                try:
                    import logging
                    logging.getLogger(__name__).warning('GTIN diagnostics unavailable for %s: %s', status.get('id'), type(error).__name__)
                except Exception:
                    pass
            status = source_freshness(status, rows)
            offers.extend(rows);sources.append(status)
    # Preserve official partner snapshots; stale dates remain visible to the UI.
    public_ids={s[0] for s in SOURCES}
    for partner in old.get('sources',[]):
        if partner['id'] not in public_ids and partner.get('method')=='Feed ufficiale normalizzato':
            rows=[r for r in old['offers'] if r['merchant_id']==partner['id']]
            offers.extend(rows);sources.append(partner)
    payload={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'refresh_hours':6,'tracking_enabled':any(o.get('affiliate_url') for o in offers),'sources':sources,'offers':offers}
    if not offers: raise SystemExit('No verified offers available; previous catalog unchanged')
    path.parent.mkdir(exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')));tmp.replace(path)
    path.with_suffix('.json.gz').write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    print(json.dumps({'offers':len(offers),'sources':sources},ensure_ascii=False))
if __name__=='__main__':main()
