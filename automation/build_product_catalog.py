"""Stable canonical products separate from merchant offers and observed history.

GTIN + explicit selling quantity define automatic identity. Missing identifiers
stay isolated; similarity produces review candidates, never a false comparison.
"""
import datetime as dt
import gzip
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter,defaultdict
from pathlib import Path
try:
    from .audit_store_integrity import canonical_gtin
    from .package_integrity import pack_count
except ImportError:
    from audit_store_integrity import canonical_gtin
    from package_integrity import pack_count
ROOT=Path(__file__).resolve().parents[1]
BASE='https://offerte4zampe.it'
IMAGE_RULES=json.loads((ROOT/'automation/image-rights.json').read_text())['stores']
try:
    from .image_policy import local_image
except ImportError:
    from image_policy import local_image
BRAND_ALIASES=json.loads((ROOT/'automation/brand_aliases.json').read_text())


def observed_history(rows, history):
    daily=defaultdict(dict)
    for o in rows:
        for item in history.get('offers',{}).get(o['id'],[]):
            if not item.get('available') or not isinstance(item.get('last'),(int,float)):continue
            prior=daily[item['day']].get(o['merchant_id'])
            if prior is None or item['last']<prior['last']:daily[item['day']][o['merchant_id']]=item
    return [{'day':day,'low':min(r['low'] for r in values.values()),'high':max(r['high'] for r in values.values()),'sum':sum(r['last'] for r in values.values()),'count':len(values)} for day,values in sorted(daily.items())]


def history_count(rows, now):
    dates=set()
    for item in rows:
        try:
            day=dt.date.fromisoformat(item['day'])
            if day<=now.date() and item['low']>0 and item['high']>=item['low'] and item['count']>0 and math.isfinite(item['sum']):dates.add(day)
        except (ValueError,TypeError,KeyError):pass
    return len(dates)


def normalized(value):
    return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().lower()).strip()


def canonical_brand(value):
    text=str(value or '').strip()
    aliases={normalized(k):v for k,v in BRAND_ALIASES.items()}
    aliases.update({normalized(v):v for v in BRAND_ALIASES.values()})
    return aliases.get(normalized(text),text)


def clean_title(title,brand='',variant=''):
    title=re.sub(r'\s+-\s+(?:1[°º]?\s*ordine\?|cibo umido|cibo secco|integratori per|croccantini per|dieta veterinaria per|lettiera agglomerante|lettiera vegetale).*$','',str(title),flags=re.I)
    title=re.sub(r'\bgr\b','g',title,flags=re.I)
    title=re.sub(r'(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l)\b(?:\s*[·|/]\s*|\s+)\1\s*\2\b',r'\1 \2',title,flags=re.I)
    if brand:
        pattern=r'^\s*'+re.escape(brand)+r'\s*[-–:|]?\s*'+re.escape(brand)+r'\b'
        title=re.sub(pattern,brand,title,flags=re.I)
    title=re.sub(r'\bgr\b','g',title,flags=re.I)
    title=re.sub(r'\s+',' ',title).strip(' -–|')
    # Preserve proper acronyms and case in product lines; normalize shouting only.
    if title.isupper():title=title.capitalize()
    if brand and normalized(title).startswith(normalized(brand)):
        match=re.match(re.escape(brand),title,re.I)
        if match:title=brand+title[match.end():]
    if variant and variant.lower() not in ('default title','1ct') and not variant.startswith('Formato e ricetta'):
        compact=lambda text: normalized(re.sub(r'(\d)\s+(kg|g|ml|l)\b',r'\1\2',text,flags=re.I))
        if compact(variant) not in compact(title):title+=' · '+variant
    return title


def quantity(o):
    blocked=o.get('quantity_verified') is False or o.get('weight_conflict')
    kg=o.get('weight_kg')
    mass=round(kg*1000,6) if isinstance(kg,(float,int)) and not isinstance(kg,bool) and math.isfinite(kg) and 0<kg<=1000 and not blocked else None
    label=o.get('variant','')
    if not re.search(r'\d\s*(?:l|lt|litri|litro|ml)\b',label,re.I):label=o.get('title','')
    text=str(label).lower().replace(',','.')
    volume=None
    if not blocked and re.search(r'lettier|litter|shampoo|balsamo|detergent|biocondizion|fertilizz|latte|soluzione|\bolio\b',o.get('title','')+' '+o.get('category',''),re.I) and '+' not in text and not re.search(r'\d\s*[-/]\s*\d',text):
        units=re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(ml|litri|litro|lt|l)\b',text)
        values={round(float(n)*(1 if u=='ml' else 1000),6) for n,u in units}
        pack=re.search(r'(\d+)\s*(?:confezioni\s+da\s+|[x×]\s*)(\d+(?:\.\d+)?)\s*(ml|litri|litro|lt|l)\b',text)
        if pack:
            each=float(pack[2])*(1 if pack[3]=='ml' else 1000);total=int(pack[1])*each
            if values and values<={round(each,6),round(total,6)}:volume=total
        if volume is None and len(values)==1:
            volume=next(iter(values));multi=re.search(r'(\d+)\s*[x×]\s*\d+(?:\.\d+)?\s*(?:ml|litri|litro|lt|l)\b',text)
            if multi:volume*=int(multi[1])
            elif pack_count(o.get('title',''))>1:volume*=pack_count(o['title'])
            elif re.search(r'\d+\s*(?:confezioni|pezzi|pz)\b',text):volume=None
    pieces=None
    if not blocked:
        declared=re.findall(r'\b(\d+)\s*(?:pz|pezzi|bustine|compresse|lattine|buste)\b',str(o.get('title','')).lower())
        counts={int(x) for x in declared}
        if len(counts)==1 and 0<next(iter(counts))<=10000:pieces=next(iter(counts))
        elif pack_count(o.get('title',''))>1:pieces=pack_count(o['title'])
    if mass:kind,value,unit='mass',mass/1000,'kg'
    elif volume and 0<volume<=1000000:kind,value,unit='volume',volume/1000,'l'
    elif pieces:kind,value,unit='pieces',pieces,'pz'
    else:kind,value,unit='sales_unit',1,'confezione'
    return dict(weight_g=mass,volume_ml=volume,pieces=pieces,kind=kind,value=value,unit=unit,verified=not blocked)


def format_label(q):
    f=lambda n:format(n,'.8g').replace('.',',')
    if q['weight_g']:return f(q['weight_g']/1000)+' kg' if q['weight_g']>=1000 else f(q['weight_g'])+' g'
    if q['volume_ml']:return f(q['volume_ml']/1000)+' l' if q['volume_ml']>=1000 else f(q['volume_ml'])+' ml'
    if q['pieces']:return str(q['pieces'])+' pezzi'
    return 'Formato da verificare' if not q['verified'] else 'Unità di vendita'


def attributes(o):
    s=normalized(o.get('title','')+' '+o.get('category',''))
    dog=bool(re.search(r'\b(cane|cani|dog|dogs|puppy)\b',s));cat=bool(re.search(r'\b(gatto|gatti|cat|cats|kitten)\b',s))
    species='cane e gatto' if dog and cat else 'cane' if dog else 'gatto' if cat else ''
    category='lettiere' if re.search(r'lettier|litter',s) else 'umido' if re.search(r'umido|mousse|pate',s) else 'crocchette' if re.search(r'crocchett|croccantin|cibo secco|dry food',s) else 'snack' if re.search(r'snack|biscott|masticativ',s) else 'accessori'
    proteins=sorted({w for w in ['pollo','salmone','agnello','manzo','tonno','coniglio','anatra','tacchino','pesce','cervo','maiale'] if re.search(r'\b'+w+r'\b',s)})
    return dict(species=species,category=category,recipe=' + '.join(proteins))


def identity(o,q):
    code=canonical_gtin(o.get('gtin'))
    if code and q['verified']:
        # Explicit multipack words without a resolved quantity must not collapse units.
        ambiguous=q['kind']=='sales_unit' and re.search(r'\b(?:confezione|set|kit|multipack|pezzi|pz)\b|\d\s*[x×]',o['title'],re.I)
        if not ambiguous:return ['gtin',code,normalized(canonical_brand(o.get('brand',''))),q['kind'],q['value']]
    return ['unattached',o['id']]


def fresh(o,now):
    try:
        stamp=dt.datetime.fromisoformat(o['checked_at'].replace('Z','+00:00'))
        return bool(stamp.tzinfo and -300<=(now-stamp).total_seconds()<=36*3600 and o.get('available') is True)
    except (TypeError,KeyError,ValueError):return False


def build(catalog,old_registry=None,history=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc);old_registry=old_registry or {};history=history or {}
    try:
        from .name_matching import resolve
    except ImportError:
        from name_matching import resolve
    try:
        from .merchant_promotions import annotate
    except ImportError:
        from merchant_promotions import annotate
    catalog={**catalog,'offers':[annotate(o) for o in catalog['offers']]}
    buckets=defaultdict(list)
    q_by_id={o['id']:quantity(o) for o in catalog['offers']}
    identities={o['id']:identity(o,q_by_id[o['id']]) for o in catalog['offers']}
    identities,name_methods,name_report=resolve(catalog['offers'],q_by_id,identities,normalized,canonical_brand,canonical_gtin)
    for o in catalog['offers']:
        buckets[json.dumps(identities[o['id']],ensure_ascii=False,separators=(',',':'))].append(o)
    products=[];offers=[];registry={};by_bucket=defaultdict(list)
    for key,rows in sorted(buckets.items()):
        pid='p-'+hashlib.sha256(key.encode()).hexdigest()[:20];previous=old_registry.get(pid,{})
        rows=sorted(rows,key=lambda o:(not fresh(o,now),len(clean_title(o['title'],o.get('brand',''),o.get('variant',''))),o['id']))
        seed=rows[0];q=q_by_id[seed['id']];attrs=attributes(seed)
        title=clean_title(seed['title'],seed.get('brand',''),seed.get('variant',''))
        product_gtin=next((canonical_gtin(o.get('gtin')) for o in rows if canonical_gtin(o.get('gtin'))),'')
        name_matched=any(o['id'] in name_methods for o in rows)
        method='gtin_with_name' if name_matched and product_gtin else 'name_characteristics' if name_matched else 'gtin_quantity' if json.loads(key)[0]=='gtin' else 'unattached'
        suffix=product_gtin or pid[2:]
        slug=previous.get('slug') or normalized(title).replace(' ','-')[:115].rstrip('-')+'-'+suffix+'-'+pid[-6:]
        active=[o for o in rows if fresh(o,now)];shops={o['merchant_id'] for o in active};verified_shops={o['merchant_id'] for o in active if q_by_id[o['id']]['verified']}
        p=dict(id=pid,slug=slug,gtin=product_gtin,brand=canonical_brand(seed.get('brand','')),name=title,**attrs,quantity=q,format=format_label(q),image=seed.get('image',''),offer_ids=[o['id'] for o in rows],active_shop_count=len(shops),verified_shop_count=len(verified_shops),active_offer_count=len(active),low_price=min((o['price'] for o in active),default=None),matching_method=method,matching_confidence=1.0 if method=='gtin_quantity' else None,reviewed=any(o.get('identity_review') for o in rows))
        # Only a licensed image from this exact canonical identity can be shared.
        image_offer=next((o for o in rows if fresh(o,now) and local_image(o,IMAGE_RULES.get(o.get('merchant_id'),{}))),None)
        if image_offer:
            p['image']=image_offer['image'];p['image_local']=image_offer['image_local'];p['image_source_offer']=image_offer['id']
        # Set after observed history is aggregated; duplicate shops never count twice.
        content=json.dumps([title,q,[(o['id'],o['price'],o['available'],(o.get('merchant_promotion') or {}).get('reference_cents'),(o.get('merchant_promotion') or {}).get('valid_until')) for o in rows]],ensure_ascii=False,sort_keys=True)
        signature=hashlib.sha256(content.encode()).hexdigest();lastmod=previous.get('lastmod')
        if not previous or signature!=previous.get('content_hash'):lastmod=now.isoformat()
        p['lastmod']=lastmod
        # Preserve the real observed history relation by offer ID, never backfill.
        p['history']=observed_history(rows,history)
        p['indexable']=len(verified_shops)>=2 or history_count(p['history'],now)>=30
        products.append(p);registry[pid]={'slug':slug,'content_hash':signature,'lastmod':lastmod,'product':{k:v for k,v in p.items() if k!='history'}}
        if q['kind']!='sales_unit':by_bucket[(normalized(p['brand']),attrs['species'],q['kind'],q['value'])].append(p)
        for o in rows:
            offer={**o,'product_id':pid,'product_slug':slug,'product_url':'/prodotto/'+slug,'canonical_title':title,'quantity':q_by_id[o['id']],'unit_price':round(o['price']/q_by_id[o['id']]['value'],6) if q_by_id[o['id']]['verified'] else None,'unit_price_unit':q_by_id[o['id']]['unit'] if q_by_id[o['id']]['verified'] else None,'canonical_shop_count':len(verified_shops)}
            if image_offer:
                offer['image_local']=p['image_local'];offer['image_source_offer']=p['image_source_offer']
            else:
                offer.pop('image_local',None);offer.pop('image_source_offer',None)
            offer['product_matching_method']=method
            offer['offer_matching_method']=name_methods.get(o['id'],'gtin' if canonical_gtin(o.get('gtin')) else 'unattached')
            offer['canonical_format']=p['format'];offer['product_identity_verified']=p['matching_method']=='gtin_quantity'
            offer['unit_prices']={unit:round(o['price']/value,6) for unit,value in [('kg',(q_by_id[o['id']]['weight_g'] or 0)/1000),('l',(q_by_id[o['id']]['volume_ml'] or 0)/1000),('pz',q_by_id[o['id']]['pieces'] or 0)] if value and q_by_id[o['id']]['verified']}
            offers.append(offer)
    # Candidates are deliberately separate from identity, pending exact evidence.
    candidates=[]
    for p in products:
        if p['matching_method']!='unattached' or not p['brand'] or p['quantity']['kind']=='sales_unit':continue
        bucket=(normalized(p['brand']),p['species'],p['quantity']['kind'],p['quantity']['value'])
        words=set(normalized(p['name']).split())
        for peer in by_bucket[bucket]:
            if peer['id']==p['id'] or peer['matching_method']=='unattached':continue
            other=set(normalized(peer['name']).split());score=len(words&other)/max(1,len(words|other))
            if p['recipe'] and peer['recipe'] and p['recipe']!=peer['recipe']:continue
            if score>=.7:candidates.append(dict(product_id=p['id'],candidate_product_id=peer['id'],confidence=round(min(.96,score),3),status='needs_evidence',reason='brand_quantity_species_and_title_similarity; missing shared GTIN'))
    offer_targets={o['id']:(o['product_id'],o['product_slug']) for o in offers}
    for pid,entry in old_registry.items():
        if pid not in registry and entry.get('product'):
            archived={**entry['product'],'offer_ids':[],'active_shop_count':0,'verified_shop_count':0,'active_offer_count':0,'low_price':None,'indexable':False,'history':[]}
            # Redirect only when every old offer is still present and now belongs
            # to one exact canonical product. Removed/split offers remain archives.
            old_ids=entry['product'].get('offer_ids',[])
            targets={offer_targets[i] for i in old_ids if i in offer_targets}
            if old_ids and all(i in offer_targets for i in old_ids) and len(targets)==1:
                archived['redirect_slug']=next(iter(targets))[1]
            archived.pop('image_local',None);archived.pop('image_source_offer',None)
            archived['history']=observed_history([{'id':oid,'merchant_id':oid.split(':',1)[0]} for oid in old_ids],history)
            archived['indexable']='redirect_slug' not in archived and history_count(archived['history'],now)>=30
            products.append(archived);registry[pid]=entry
    families=defaultdict(list)
    for p in products:
        family=re.sub(r'\d+(?:[.,]\d+)?\s*(?:kg|gr|g|ml|litri|lt|l)\b','',p['name'],flags=re.I)
        family=re.sub(r'confezione da \d+ pezzi','',family,flags=re.I)
        families[(normalized(p['brand']),normalized(family))].append(p)
    for p in products:
        family=re.sub(r'\d+(?:[.,]\d+)?\s*(?:kg|gr|g|ml|litri|lt|l)\b','',p['name'],flags=re.I)
        family=re.sub(r'confezione da \d+ pezzi','',family,flags=re.I)
        p['related']=[{k:o[k] for k in ('id','slug','name','format','low_price')} for o in families[(normalized(p['brand']),normalized(family))] if o['id']!=p['id'] and o['active_offer_count']][:4]
    candidates=sorted(candidates,key=lambda x:(-x['confidence'],x['product_id'],x['candidate_product_id']))
    active_products=[p for p in products if p['active_offer_count']]
    multi=[p for p in active_products if p['verified_shop_count']>=2]
    store_coverage={}
    for shop in sorted({o['merchant_id'] for o in catalog['offers']}):
        rows=[o for o in offers if o['merchant_id']==shop]
        store_coverage[shop]={
            'offers':len(rows),
            'active_offers':sum(fresh(o,now) for o in rows),
            'missing_valid_gtin':sum(not bool(canonical_gtin(o.get('gtin'))) for o in rows),
            'unverified_quantity':sum(not o['quantity']['verified'] for o in rows),
            'sales_unit_only':sum(o['quantity']['kind']=='sales_unit' for o in rows),
            'offers_in_multishop_products':sum(fresh(o,now) and o['canonical_shop_count']>=2 for o in rows),
        }
    metric=dict(name_matching=name_report,gtin_multi_shop_products=sum(p['matching_method']=='gtin_quantity' for p in multi),characteristic_multi_shop_products=sum(p['matching_method'] in ('gtin_with_name','name_characteristics') for p in multi),store_coverage=store_coverage,products=len(products),active_products=len(active_products),offers=len(offers),multi_shop_products=len(multi),multi_shop_percent=round(100*len(multi)/max(1,len(active_products)),2),denominator='active canonical products, distinct merchants with verified quantities; GTIN and characteristic matching reported separately; duplicate offers in one shop do not count',unattached_offers=sum(p['active_offer_count'] for p in products if p['matching_method']=='unattached'),candidate_pairs=len(candidates),automatic_match_rules='GTIN and quantity, or exact normalized name plus brand and verified selling quantity; conflicting GTINs excluded')
    return dict(schema_version=1,generated_at=catalog['generated_at'],products=products,offers=offers,metrics=metric,matching_candidates=candidates,registry=registry)


def write(model,site):
    product_shards={format(i,'02x'):{} for i in range(256)};route_shards={format(i,'02x'):{} for i in range(256)}
    by_offer={o['id']:o for o in model['offers']}
    for p in model['products']:
        prefix=hashlib.sha256(p['slug'].encode()).hexdigest()[:2]
        product_shards[prefix][p['slug']]={**p,'offers':[by_offer[i] for i in p['offer_ids']]}
        for oid in p['offer_ids']:route_shards[hashlib.sha256(oid.encode()).hexdigest()[:2]][oid]=p['slug']
    for name,data in [('canonical-products',product_shards),('canonical-routes',route_shards)]:
        folder=site/'data'/name;folder.mkdir(exist_ok=True)
        for prefix,rows in data.items():(folder/(prefix+'.json')).write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':'))+'\n')
    (site/'data/canonical-route-list.json').write_text(json.dumps([p['slug'] for p in model['products']],separators=(',',':'))+'\n')
    (site/'data/canonical-sitemap.json').write_text(json.dumps([{'url':BASE+'/prodotto/'+p['slug'],'lastmod':p['lastmod'],'content_hash':model['registry'][p['id']]['content_hash']} for p in model['products'] if p['indexable']],separators=(',',':'))+'\n')
    (site/'data/product-coverage.json').write_text(json.dumps({'generated_at':model['generated_at'],**model['metrics']},ensure_ascii=False,indent=2)+'\n')
    (site/'data/matching-candidates.json').write_text(json.dumps(model['matching_candidates'],ensure_ascii=False,indent=2)+'\n')
    # Separate relations remain available as a portable snapshot, without needing SQL.
    snapshot={k:v for k,v in model.items() if k not in ('registry','matching_candidates')}
    snapshot['price_history_relation']={'foreign_key':'offer.id','shards':'/data/history/{sha256_offer_id_prefix}.json.gz','scope':'Observed per-offer history; daily summaries, no invented intermediate prices'}
    (site/'data/product-catalog.json.gz').write_bytes(gzip.compress(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))


def main():
    catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()));state=ROOT/'automation/product-registry.json'
    previous=json.loads(state.read_text()) if state.exists() else {}
    history_path=ROOT/'site/data/price-history.json.gz'
    history=json.loads(gzip.decompress(history_path.read_bytes())) if history_path.exists() else {}
    model=build(catalog,previous,history);write(model,ROOT/'site');state.write_text(json.dumps(model['registry'],ensure_ascii=False,separators=(',',':'))+'\n')
    # Consumers keep merchant IDs; canonical identity is an explicit separate relation.
    catalog['offers']=model['offers'];(ROOT/'site/data/catalog.json.gz').write_bytes(gzip.compress(json.dumps(catalog,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    print('Canonical product coverage:',json.dumps(model['metrics']))


if __name__=='__main__':main()
