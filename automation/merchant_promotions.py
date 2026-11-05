"""Compare a selected merchant offer to its explicitly declared reference price."""
import datetime as dt
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from urllib.parse import urlsplit,parse_qs

KINDS={'shopify_compare_at','feed_regular_price'}
SHOPS={'webpet':{'webpet.it','www.webpet.it'},'animaliapet':{'animaliapet.eu','www.animaliapet.eu'},'bauzaar':{'bauzaar.it','www.bauzaar.it'}}

def cents(value):
    try:
        if isinstance(value,bool):return None
        n=Decimal(str(value))
        return int((n*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if n.is_finite() and 0<n<100000 else None
    except (InvalidOperation,ValueError,TypeError):return None

def with_reference(o,reference,kind,valid_until=None):
    row=dict(o);row.pop('merchant_promotion',None)
    price,ref=cents(o.get('price')),cents(reference)
    if kind in KINDS and price and ref and ref>price:
        row['merchant_promotion']=dict(kind=kind,offer_id=o['id'],price_cents=price,reference_cents=ref,source_url=o['url'],observed_at=o['checked_at'],valid_until=valid_until)
    return row

def annotate(o):
    # previous_price has always been read from this exact Shopify variant's
    # compare_at_price, and is not interpreted as a historical minimum.
    if o.get('source_type')!='official_feed' and o.get('merchant_id') in SHOPS:
        try:
            u=urlsplit(o['url']);variant=o['id'].split(':',1)[1]
            if u.scheme=='https' and u.hostname in SHOPS[o['merchant_id']] and u.path.startswith('/products/') and parse_qs(u.query).get('variant')==[variant]:
                return with_reference(o,o.get('previous_price'),'shopify_compare_at')
        except (KeyError,ValueError,IndexError):pass
    return dict(o)

def info(o,now=None):
    p=o.get('merchant_promotion');now=now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(p,dict) or p.get('kind') not in KINDS or o.get('available') is not True or o.get('quantity_verified') is False or o.get('weight_conflict'):return None
    if p.get('offer_id')!=o.get('id') or p.get('price_cents')!=cents(o.get('price')) or p.get('source_url')!=o.get('url') or p.get('observed_at')!=o.get('checked_at'):return None
    try:
        stamp=dt.datetime.fromisoformat(p['observed_at'].replace('Z','+00:00'))
        if not stamp.tzinfo or not -300<=(now-stamp).total_seconds()<=12*3600:return None
        if p.get('valid_until'):
            end=dt.datetime.fromisoformat(p['valid_until'].replace('Z','+00:00'))
            if not end.tzinfo or now>end:return None
        price,ref=p['price_cents'],p['reference_cents']
        if type(price)!=int or type(ref)!=int or not 0<price<ref<10000000:return None
    except (KeyError,TypeError,ValueError):return None
    return dict(reference_cents=ref,saved_cents=ref-price,percent=((ref-price)*1000//ref)/10)

def render(o,now=None):
    p=info(o,now)
    if not p:return ''
    euro=lambda n:f'{n/100:.2f}'.replace('.',',')+' €'
    percent=format(p['percent'],'g').replace('.',',')
    return '<span class="merchant-promo" data-merchant-promo><span class="merchant-promo-badge">−'+percent+'% · PROMO NEGOZIO</span><span class="merchant-promo-reference">Rif. negozio <s>'+euro(p['reference_cents'])+'</s></span><span class="merchant-promo-saving">Risparmi '+euro(p['saved_cents'])+' sul riferimento</span></span>'
