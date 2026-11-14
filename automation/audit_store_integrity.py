"""Independent all-store field audit and rotating product-page verification.

A feed import succeeding is not a verification of the merchant page. Unknown
responses remain unknown; product names alone never establish equivalence.
"""
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import html
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
try:
    from .check_merchant_links import Checker, safe_product, UA
    from .package_integrity import pack_count
    from .update_catalog import weight
except ImportError:
    from check_merchant_links import Checker, safe_product, UA
    from package_integrity import pack_count
    from update_catalog import weight

ROOT=Path(__file__).resolve().parents[1]
STORES=('bauzaar','webpet','animaliapet','isola-dei-tesori','paco')


def canonical_gtin(value):
    code=str(value or '').strip()
    if len(code) not in (8,12,13,14) or not code.isascii() or not code.isdigit() or len(set(code))==1:return ''
    check=(10-sum(int(n)*(3 if i%2==0 else 1) for i,n in enumerate(reversed(code[:-1])))%10)%10
    return code.zfill(14) if check==int(code[-1]) else ''


def fingerprint(o):
    # Derived GTIN/weight may be repaired; bind evidence to the exact selling row.
    keys=('id','title','url','brand','price','available')
    native_code=o.get('feed_gtin') if 'feed_gtin' in o else (o.get('gtin') if o.get('gtin_source','catalog')=='catalog' else '')
    native_variant=o.get('feed_unit_pricing_measure',o.get('variant','')) if o['merchant_id']=='bauzaar' else ('' if o['merchant_id']=='paco' else o.get('variant',''))
    return hashlib.sha256(json.dumps([o.get(k) for k in keys]+[canonical_gtin(native_code),native_variant],ensure_ascii=False).encode()).hexdigest()


def page_url(o):
    if not safe_product(o):return None
    return o['url'].split('?')[0]+'.js' if o['merchant_id'] in ('bauzaar','webpet','animaliapet') else o['url']


def verify_page(o,body):
    result={'status':'inconclusive','compared':[],'discrepancies':[],'evidence':{}}
    try:
        if o['merchant_id'] in ('bauzaar','webpet','animaliapet'):
            data=json.loads(body)
            v=next((v for v in data.get('variants',[]) if str(v.get('id'))==o['id'].split(':',1)[1]),None)
            if not v:return dict(result,reason='exact_variant_not_in_page')
            if not isinstance(v.get('price'),(int,float)) or not isinstance(v.get('available'),bool):return dict(result,reason='missing_explicit_price_or_stock')
            count=pack_count(o['title']) if o['merchant_id']=='bauzaar' else 1
            price=round(v['price']/100*count,2)
            label=v.get('title','')
            kg=weight(label)
            # A recipe-only option uses the explicitly declared selling-pack title.
            if not kg:kg=weight(o['title'])
            elif count>1:kg=round(kg*count,6)
            evidence={'price':price,'unit_price':v['price']/100,'pack_count':count,'available':v['available'],
                      'gtin':canonical_gtin(v.get('barcode')),'net_weight_kg':kg,'variant_label':label,'exact_variant':str(v['id'])}
        else:
            products=[]
            for block in re.findall(r'<script\b[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>',body,re.I|re.S):
                try:
                    value=json.loads(block)
                    objects=value if isinstance(value,list) else [value]
                    for item in list(objects):
                        if isinstance(item,dict):objects.extend(item.get('@graph',[]))
                    products.extend(x for x in objects if isinstance(x,dict) and x.get('@type')=='Product')
                except (TypeError,ValueError):continue
            ident=o['id'].split(':',1)[1]
            selected=None
            if o['merchant_id']=='paco':
                attr=re.search(r'data-product="([^"]+)"',body)
                if not attr:return dict(result,reason='selected_variant_payload_missing')
                selected=json.loads(html.unescape(attr[1]))
                if str(selected.get('id'))!=ident:return dict(result,reason='selected_product_id_mismatch')
                codes={canonical_gtin(a.get('ean13')) for a in selected.get('attributes',{}).values() if a.get('ean13')}
                expected=canonical_gtin(o.get('feed_gtin') or o.get('gtin'))
                if not expected or codes!={expected}:return dict(result,reason='selected_pack_not_bound_to_feed_barcode')
            products=[p for p in products if selected is not None or str(p.get('sku'))==ident or str(p.get('mpn'))==ident]
            if len(products)!=1:return dict(result,reason='exact_product_schema_missing_or_ambiguous')
            product=products[0];offer=product.get('offers',{})
            if not isinstance(offer,dict) or offer.get('priceCurrency')!='EUR':return dict(result,reason='single_eur_offer_missing')
            stock=str(offer.get('availability','')).rsplit('/',1)[-1]
            if stock not in ('InStock','OutOfStock'):return dict(result,reason='explicit_stock_missing')
            evidence={'price':float(offer['price']),'available':stock=='InStock','gtin':canonical_gtin(product.get('gtin13') or product.get('gtin14')),'exact_product':ident}
            if o['merchant_id']=='paco':
                # Its URL can default to a different pack/recipe. Bind it to feed EAN.
                expected=canonical_gtin(o.get('feed_gtin') or o.get('gtin'))
                if not expected or expected!=evidence['gtin']:return dict(result,reason='selected_pack_not_bound_to_feed_barcode')
                try:
                    from .paco_feed import verify_quantity
                except ImportError:
                    from paco_feed import verify_quantity
                verified=verify_quantity(o,body)
                if verified.get('quantity_verified'):
                    evidence.update(net_weight_kg=verified['weight_kg'],variant_label=verified['variant'],quantity_verified=True)
        if not math.isfinite(evidence['price']) or evidence['price']<=0:return dict(result,reason='invalid_page_price')
        result.update(status='verified',evidence=evidence,compared=['price','available'])
        for field in ('price','available'):
            differs=abs(evidence[field]-o[field])>.005 if field=='price' else evidence[field]!=o[field]
            if differs:result['discrepancies'].append(field)
        existing=canonical_gtin(o.get('gtin') or o.get('feed_gtin'))
        if existing and evidence.get('gtin'):
            result['compared'].append('gtin')
            if existing!=evidence['gtin']:result['discrepancies'].append('gtin')
        if evidence.get('net_weight_kg') and o.get('weight_kg'):
            result['compared'].append('weight_kg')
            if abs(evidence['net_weight_kg']-o['weight_kg'])>1e-6:result['discrepancies'].append('weight_kg')
        return result
    except (ValueError,TypeError,KeyError,AttributeError):return dict(result,reason='unreadable_product_evidence')


def usable(entry,o,now,hours=24):
    try:
        stamp=dt.datetime.fromisoformat(entry['checked_at'])
        return bool(entry.get('fingerprint')==fingerprint(o) and stamp.tzinfo and dt.timedelta(0)<=now-stamp<=dt.timedelta(hours=hours))
    except (KeyError,TypeError,ValueError):return False


def select(offers,cache,now,per_store=4):
    groups={s:[] for s in STORES}
    for o in offers:
        if o['merchant_id'] not in groups or not page_url(o):continue
        entry=cache.get(o['id'],{})
        if usable(entry,o,now):continue
        # Rotate every eligible record, including failed attempts and sold-out rows.
        old=entry.get('checked_at','') if entry.get('fingerprint')==fingerprint(o) else ''
        bucket=hashlib.sha256((now.date().isoformat()+o['id']).encode()).hexdigest()
        priority=0 if o.get('weight_conflict') or entry.get('discrepancies') else 1
        groups[o['merchant_id']].append((priority,old,bucket,o))
    return {s:[r[-1] for r in sorted(groups[s],key=lambda x:x[:3])[:per_store]] for s in STORES}


def apply_evidence(offers,cache,now):
    repaired=[]
    for o in offers:
        e=cache.get(o['id'],{})
        if not usable(e,o,now,7*24) or e.get('status')!='verified':continue
        proof=e.get('evidence',{})
        # Prices and stock are audited, never silently rewritten from page defaults.
        if any(x in e.get('discrepancies',[]) for x in ('price','available','gtin')):continue
        code=canonical_gtin(proof.get('gtin'));existing=canonical_gtin(o.get('gtin') or o.get('feed_gtin'))
        if existing and code and existing!=code:continue
        changed=[]
        if not o.get('gtin') and code and (o.get('quantity_verified') is not False or proof.get('quantity_verified')):
            o.update(gtin=code,gtin_source=e['source'],gtin_checked_at=e['checked_at']);changed.append('gtin')
        kg=proof.get('net_weight_kg')
        if not isinstance(kg,(int,float)) or isinstance(kg,bool) or not math.isfinite(kg) or not 0<kg<=1000:kg=None
        if kg and (o.get('quantity_verified') is not False or proof.get('quantity_verified')) and (o.get('weight_conflict') or not o.get('weight_kg')):
            o.update(weight_kg=kg,weight_source='merchant:selected_variant',weight_checked_at=e['checked_at']);o.pop('weight_conflict',None);changed.append('weight_kg')
            if proof.get('variant_label') and o['merchant_id']=='bauzaar':
                o.setdefault('feed_unit_pricing_measure',o.get('variant',''));o['variant']=proof['variant_label']
        if proof.get('quantity_verified'):
            o.update(quantity_verified=True,quantity_checked_at=e['checked_at'],variant=proof['variant_label'])
        if changed:repaired.append({'id':o['id'],'fields':changed,'source':e['source']})
    return repaired



def suppress_commercial_conflicts(catalog, cache, now):
    """Withhold exact, recent contradictory rows; never rewrite feed fields.

    As with merchant-link suppression, the next import reconstructs all rows.
    Expired/changed/inconclusive evidence cannot withhold a different observation.
    The report retains each original row and proof for review and rollback.
    """
    withheld=[];kept=[]
    for o in catalog['offers']:
        entry=cache.get(o['id'],{});proof=entry.get('evidence',{})
        exact_key='exact_variant' if o.get('merchant_id') in ('bauzaar','webpet','animaliapet') else 'exact_product'
        exact=str(proof.get(exact_key,''))==o['id'].split(':',1)[1]
        code=canonical_gtin(o.get('gtin') or o.get('feed_gtin'))
        proof_code=canonical_gtin(proof.get('gtin'))
        expected_source=page_url(o)
        trusted=(o.get('merchant_id') in STORES and usable(entry,o,now,24)
                 and bool(expected_source) and entry.get('status')=='verified' and entry.get('source')==expected_source
                 and exact and not (code and proof_code and code!=proof_code))
        reasons=[]
        if trusted:
            price=proof.get('price');stock=proof.get('available')
            if ('price' in entry.get('compared',[]) and 'price' in entry.get('discrepancies',[])
                and isinstance(price,(int,float)) and not isinstance(price,bool)
                and math.isfinite(price) and price>0 and abs(price-o['price'])>.005):reasons.append('price')
            if ('available' in entry.get('compared',[]) and 'available' in entry.get('discrepancies',[])
                and isinstance(stock,bool) and stock!=o.get('available')):reasons.append('available')
        if reasons:
            withheld.append({'id':o['id'],'reasons':reasons,'offer':dict(o),
                             'source':entry['source'],'checked_at':entry['checked_at'],
                             'fingerprint':entry['fingerprint'],'evidence':dict(proof)})
        else:kept.append(o)
    output={**catalog,'offers':kept}
    suppression={'checked_at':now.isoformat(),'evidence_max_age_hours':24,
                 'input_offers':len(catalog['offers']),'published_offers':len(kept),
                 'withheld':withheld,
                 'method':'Only exact-identity price/stock contradictions with matching source and row fingerprint, verified within 24 hours. Raw fields are retained here without rewriting. No Amazon evidence is collected or applied. Expiry or a changed row requires a new check; missing/inconclusive evidence is not a contradiction.'}
    return output,suppression


def report(catalog,cache,now,repairs=()):
    rows=catalog['offers'];stores=[];duplicates=Counter(o['id'] for o in rows)
    for sid in STORES:
        offers=[o for o in rows if o['merchant_id']==sid]
        checked=[dict(id=o['id'],source=cache[o['id']]['source'],**{k:cache[o['id']].get(k) for k in ('checked_at','status','compared','discrepancies','reason','evidence')}) for o in offers if usable(cache.get(o['id'],{}),o,now,36)]
        by_id={o['id']:o for o in offers}
        for record in checked:
            o=by_id[record['id']]
            record['detected_discrepancies']=list(record['discrepancies'] or [])
            if 'weight_kg' in (record['discrepancies'] or []) and o.get('weight_kg')==record.get('evidence',{}).get('net_weight_kg'):
                record['discrepancies']=[x for x in record['discrepancies'] if x!='weight_kg']
        structural=Counter()
        for o in offers:
            if duplicates[o['id']]>1:structural['duplicate_offer_id']+=1
            try:
                observed=dt.datetime.fromisoformat(o['checked_at'].replace('Z','+00:00'))
                if not observed.tzinfo or not -300<=(now-observed).total_seconds()<=36*3600:structural['stale_or_future_observation']+=1
            except (KeyError,ValueError,TypeError):structural['missing_observation_time']+=1
            if not safe_product(o):structural['unsafe_or_unmapped_direct_url']+=1
            if not isinstance(o.get('available'),bool):structural['availability_not_boolean']+=1
            if not isinstance(o.get('price'),(float,int)) or isinstance(o.get('price'),bool) or not math.isfinite(o['price']) or o['price']<=0:structural['invalid_price']+=1
            if o.get('gtin') and not canonical_gtin(o['gtin']):structural['invalid_gtin']+=1
            if o.get('weight_conflict'):structural['conflicting_weight']+=1
        source=next((s for s in catalog.get('sources',[]) if s['id']==sid),{})
        if not offers:structural['store_without_published_offers']+=1
        stores.append({'id':sid,'source_status':source.get('status','unknown'),'offers':len(offers),'available':sum(o['available'] for o in offers),'with_valid_gtin':sum(bool(canonical_gtin(o.get('gtin'))) for o in offers),'with_net_weight':sum(bool(o.get('weight_kg')) for o in offers),'quantity_unverified':sum(o.get('quantity_verified') is False for o in offers),'field_issues':dict(structural),'page_verifications':checked,'sample_verified':sum(x['status']=='verified' for x in checked),'sample_inconclusive':sum(x['status']!='verified' for x in checked),'sample_discrepancies':sum(bool(x['discrepancies']) for x in checked)})
    return {'checked_at':now.isoformat(),'catalog_generated_at':catalog['generated_at'],'method_version':1,'method':'Controlli su tutte le offerte dei cinque negozi; verifica indipendente a campione e a rotazione tramite variante JSON esatta o schema prodotto vincolato a SKU/GTIN. HTTP200, feed riuscito e nome simile non certificano identità, prezzo o stock. Campione non rappresentativo statisticamente; risposte inconcludenti non sono successi. Prezzi e date originali non modificati.','stores':stores,'repairs':list(repairs)}


def refresh_coverage(catalog,now):
    quality_path=ROOT/'site/data/catalog-quality.json'
    quality=json.loads(quality_path.read_text()) if quality_path.exists() else {}
    groups={}
    for o in catalog['offers']:
        if canonical_gtin(o.get('gtin')) and o.get('weight_kg') and not o.get('weight_conflict') and o.get('quantity_verified') is not False:
            groups.setdefault((canonical_gtin(o['gtin']),o['weight_kg'],o['brand'].strip().casefold()),[]).append(o)
    matched=[g for g in groups.values() if len({o['merchant_id'] for o in g})>1]
    quality.update(offers=len(catalog['offers']),with_valid_gtin=sum(bool(canonical_gtin(o.get('gtin'))) for o in catalog['offers']),cross_shop_groups=len(matched),reviewed_identities=sum(bool(o.get('identity_review')) for o in catalog['offers']))
    quality['merchant_coverage']={sid:{'offers':sum(o['merchant_id']==sid for o in catalog['offers']),'with_gtin':sum(o['merchant_id']==sid and bool(canonical_gtin(o.get('gtin'))) for o in catalog['offers']),'with_weight':sum(o['merchant_id']==sid and bool(o.get('weight_kg')) for o in catalog['offers']),'in_cross_shop_groups':sum(o['merchant_id']==sid for group in matched for o in group)} for sid in STORES}
    quality['independent_audit_at']=now.isoformat()
    quality_path.write_text(json.dumps(quality,ensure_ascii=False)+'\n')

def build(offline=False):
    import urllib.request
    path=ROOT/'site/data/catalog.json.gz';catalog=json.loads(gzip.decompress(path.read_bytes()));cachepath=ROOT/'automation/store-verification-cache.json'
    cache=json.loads(cachepath.read_text()) if cachepath.exists() else {};now=dt.datetime.now(dt.timezone.utc);chosen=select(catalog['offers'],cache,now)
    def inspect_store(sid):
        checker=Checker();results=[]
        for o in chosen[sid]:
            url=page_url(o);record={'checked_at':now.isoformat(),'fingerprint':fingerprint(o),'source':url}
            if not checker.allowed(url):record.update(status='inconclusive',reason='robots_unverified_or_disallowed',compared=[],discrepancies=[])
            else:
                try:
                    request=urllib.request.Request(url,headers={'User-Agent':UA})
                    with checker.opener.open(request,timeout=8) as response:
                        body=response.read(3000001)
                    if len(body)>3000000:raise ValueError('page too large')
                    record.update(verify_page(o,body.decode('utf-8')))
                except Exception:record.update(status='inconclusive',reason='network_or_http_error',compared=[],discrepancies=[])
            results.append((o['id'],record));time.sleep(.25)
        return results
    if not offline:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for results in pool.map(inspect_store,STORES):cache.update(results)
    live_ids={o['id'] for o in catalog['offers']}
    cache={k:v for k,v in cache.items() if k in live_ids}
    repairs=apply_evidence(catalog['offers'],cache,now)
    cachepath.write_text(json.dumps(cache,ensure_ascii=False,separators=(',',':'))+'\n')
    output=report(catalog,cache,now,repairs)
    published,suppression=suppress_commercial_conflicts(catalog,cache,now)
    output['commercial_suppression']=suppression
    path.write_bytes(gzip.compress(json.dumps(published,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    refresh_coverage(published,now)
    if suppression['withheld']:
        print('::warning::Withheld '+str(len(suppression['withheld']))+' offers with exact recent price/stock contradictions; original rows and evidence in site/data/store-audit.json')
    (ROOT/'site/data/store-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    for s in output['stores']:
        print(s['id'],s['offers'],'field issues',s['field_issues'],'pages verified',s['sample_verified'],'inconclusive',s['sample_inconclusive'],'discrepancies',s['sample_discrepancies'])
        if s['field_issues'] or s['sample_discrepancies']:print('::warning::Independent store audit: '+s['id']+' has unresolved discrepancies; see site/data/store-audit.json')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true',help='Replay recorded exact page evidence without network')
    build(parser.parse_args().offline)
