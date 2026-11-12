"""Full-catalog exact characteristic matching; similarity never merges identities."""
import json,re
from collections import defaultdict,Counter
try:
 from .package_integrity import pack_count
except ImportError:
 from package_integrity import pack_count


# Only lexical equivalents: line names, recipes, ages and package markers remain.
TOKEN_EQUIVALENTS = {
    'dogs':'cane', 'dog':'cane', 'cani':'cane',
    'cats':'gatto', 'cat':'gatto', 'gatti':'gatto',
    'adulti':'adult', 'adulto':'adult', 'adulta':'adult',
    'chicken':'pollo', 'salmon':'salmone', 'lamb':'agnello',
    'beef':'manzo', 'tuna':'tonno', 'rabbit':'coniglio',
    'duck':'anatra', 'turkey':'tacchino', 'rice':'riso',
    'trout':'trota', 'herring':'aringa', 'cod':'merluzzo',
    'sterilized':'sterilised', 'sterilizzati':'sterilised', 'sterilizzato':'sterilised',
    'gattini':'kitten', 'gattino':'kitten', 'cuccioli':'puppy', 'cucciolo':'puppy',
}

def signature(o,q,normalize,brand):
    if not q['verified'] or q['kind']=='sales_unit':return None
    b=normalize(brand(o.get('brand','')))
    if not b:return None
    text=str(o.get('title',''))+' '+str(o.get('variant',''))
    # Do not turn target animal weight into a package size.
    if re.search(r'[<>≤≥]\s*\d|\bpeso\s+(?:del\s+cane|corporeo)|\bcani\s+da\s+\d',text,re.I):return None
    text=re.sub(r'\s+-\s+(?:cibo|croccantini|integratori|dieta veterinaria|lettiera)\b.*$','',text,flags=re.I)
    text=re.sub(r'\bdefault title\b|\b1ct\b',' ',text,flags=re.I)
    text=re.sub(r'(?<!\w)\d+(?:[.,]\d+)?\s*(?:kg|gr|g|ml|litri|litro|lt|l)\b',' ',text,flags=re.I)
    text=re.sub(r'\bconfezione\s+da\s+\d+\s*(?:pezzi|pz)\b',' ',text,flags=re.I)
    tokens=set(normalize(text).split())-set(b.split())
    tokens={TOKEN_EQUIVALENTS.get(t,t) for t in tokens}
    # Only generic merchandising nouns; retain wet/dry, lines, recipes, ages,
    # dimensions, sex, fragrance, numbers and every selected variant token.
    tokens-={'alimento','alimenti','mangime','mangimi','cibo','food','crocchette','croccantini'}
    tokens-={'per','con','di','da','e','il','la','le','in','al','alla','del','dei','the','for','with'}
    generic={'adult','adulto','adulti','cane','cani','dog','dogs','gatto','gatti','cat','cats','cibo','secco','umido','crocchette','croccantini','food','pollo','salmone','agnello','manzo','tonno','pesce','riso'}
    # Generic brand + adult + recipe is insufficient to identify a product line.
    if len(tokens)<2 or len(tokens-generic)<2:return None
    return json.dumps([b,q['kind'],q['value'],q.get('pieces'),pack_count(o.get('title','')),sorted(tokens)],ensure_ascii=False,separators=(',',':'))


def resolve(offers,quantities,identities,normalize,brand,gtin):
    groups=defaultdict(list);methods={};report=Counter(evaluated_offers=len(offers))
    for o in offers:
        key=signature(o,quantities[o['id']],normalize,brand)
        if key:groups[key].append(o);report['eligible_offers']+=1
        else:report['insufficient_characteristics']+=1
    for key,rows in groups.items():
        if len({o['merchant_id'] for o in rows})<2:continue
        # A secondary volume or piece count must not disappear behind mass.
        full_quantities={tuple(quantities[o['id']].get(k) for k in ('weight_g','volume_ml','pieces')) for o in rows}
        if len(full_quantities)>1:report['conflicting_quantity_groups']+=1;continue
        missing=[o for o in rows if not gtin(o.get('gtin'))]
        if not missing:continue
        codes={gtin(o.get('gtin')) for o in rows if gtin(o.get('gtin'))}
        if len(codes)>1:report['conflicting_gtin_groups']+=1;continue
        known={json.dumps(identities[o['id']],ensure_ascii=False,separators=(',',':')) for o in rows if gtin(o.get('gtin'))}
        if len(known)>1:report['ambiguous_identity_groups']+=1;continue
        target=json.loads(next(iter(known))) if known else ['name_characteristics',key]
        for o in rows:
            if not gtin(o.get('gtin')):identities[o['id']]=target;methods[o['id']]='name_characteristics';report['attached_without_gtin']+=1
    return identities,methods,dict(report)
