"""Review queue from independent evidence; no write to GTINs or product identities."""
import datetime as dt
import json
from collections import defaultdict
try:
    from .name_matching import signature
    from .matching_evidence import image_fingerprint
except ImportError:
    from name_matching import signature
    from matching_evidence import image_fingerprint

# Explicit incompatibilities, including cases missed by recipe extraction alone.
PROTECTED=[
    {'pollo','salmone','agnello','manzo','tonno','coniglio','anatra','tacchino','pesce','cervo','maiale','trota','aringa','merluzzo','prosciutto','cereali'},
    {'lavanda','talco','vaniglia','mandarino','neutro','unscented'},
    {'puppy','kitten','adult','senior','mature','young'},
    {'renal','struvite','urinary','diabetic','obesity','convalescence','hypoallergenic','light','sterilised'},
    {'s','m','l','xl','xxl','small','medium','large','extralarge','mini','maxi'},
    {'cane','gatto','conigli','canarini','cocorite','parrocchetti','pappagalli'},
    {'umido','secco','mousse','pate','spezzatino','chew'},
]

def incompatible(a,b):
    for vocabulary in PROTECTED:
        left,right=a&vocabulary,b&vocabulary
        if left and right and left!=right:return True
    # Dimensions, model references and numbered life stages are never disposable.
    left,right={w for w in a if any(c.isdigit() for c in w)},{w for w in b if any(c.isdigit() for c in w)}
    return bool(left and right and left!=right)

def _description(row,now):
    e=row.get('description_evidence') or {}
    try:
        stamp=dt.datetime.fromisoformat(e['checked_at'].replace('Z','+00:00'))
        if not stamp.tzinfo or not 0<=(now-stamp).total_seconds()<=30*86400:return None
        digest=e['sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):return None
        if e.get('source')!=row.get('url') or e.get('characters',0)<120:return None
        return digest
    except (KeyError,TypeError,ValueError,AttributeError):return None

def build(offers,quantities,now,normalize,brand,gtin,site,rules,limit=500):
    buckets=defaultdict(list);cache={};result=[]
    for o in offers:
        if o.get('merchant_id')=='amazon' or o.get('available') is not True:continue
        try:
            stamp=dt.datetime.fromisoformat(o['checked_at'].replace('Z','+00:00'))
            if not stamp.tzinfo or not -300<=(now-stamp).total_seconds()<=36*3600:continue
        except (KeyError,TypeError,ValueError):continue
        key=signature(o,quantities[o['id']],normalize,brand)
        if not key:continue
        fields=json.loads(key);tokens=set(fields.pop())
        fields.append([quantities[o['id']].get(k) for k in ('weight_g','volume_ml','pieces')])
        # Share quantity/brand/pack buckets, never a similarity-only global join.
        buckets[json.dumps(fields)].append((o,tokens))
    for rows in buckets.values():
        for i,(a,at) in enumerate(rows):
            for b,bt in rows[i+1:]:
                if a['merchant_id']==b['merchant_id'] or a['product_id']==b['product_id']:continue
                ac,bc=gtin(a.get('gtin')),gtin(b.get('gtin'))
                if ac and bc:continue  # Valid identifiers remain authoritative.
                if incompatible(at,bt):continue
                score=len(at&bt)/max(1,len(at|bt))
                if score<.5 or len(at&bt)<2:continue
                result.append((score,a,b,at,bt))
    # Bound image work independently from catalog size. No downloads or HTTP.
    result.sort(key=lambda p:(-p[0],p[1]['id'],p[2]['id']))
    output=[]
    for score,a,b,at,bt in result[:limit]:
        reasons=['brand_and_verified_selling_quantity','specific_title_overlap']
        if a.get('image') and a.get('image')==b.get('image'):reasons.append('same_source_image_url_not_identity_proof')
        for o in (a,b):
            if o['id'] not in cache:cache[o['id']]=image_fingerprint(o,site,rules)
        ai,bi=cache[a['id']],cache[b['id']];distance=None
        if ai and bi:
            distance=(ai['dhash']^bi['dhash']).bit_count()
            if ai['sha256']==bi['sha256']:reasons.append('same_licensed_cached_image_not_identity_proof')
            elif distance<=6:reasons.append('similar_licensed_cached_images_not_identity_proof')
        ad,bd=_description(a,now),_description(b,now)
        if ad and ad==bd:reasons.append('same_description_not_selected_variant_proof')
        output.append(dict(product_id=a['product_id'],candidate_product_id=b['product_id'],
                           offer_ids=[a['id'],b['id']],name_similarity=round(score,3),
                           status='needs_evidence',reason='; '.join(reasons),
                           image_distance=distance,missing_evidence='independent confirmation of exact line, recipe, variant and complete selling pack'))
    # Independent supporting evidence prioritizes review; never becomes a probability.
    return sorted(output,key=lambda p:(-len(p['reason'].split(';')),-p['name_similarity'],p['offer_ids']))
