"""TradeTracker's approved Bauzaar feed. Retain exact variant and net-weight evidence."""
import datetime as dt
import json
import re
import urllib.request
from urllib.parse import urlsplit, parse_qs
from decimal import Decimal, InvalidOperation

try:
    from automation.image_policy import feed_image
except ImportError:
    from image_policy import feed_image

try:
    from .merchant_promotions import with_reference
except ImportError:
    from merchant_promotions import with_reference

FEED_URL = 'https://pf.tradetracker.net/?aid=518044&encoding=utf-8&type=json&fid=600171&categoryType=2&additionalType=2'

def value(props, key):
    values = props.get(key, [])
    return str(values[0]).strip() if isinstance(values, list) and values else ''

def amount(v):
    try:
        d = Decimal(str(v))
        return float(d) if d.is_finite() and 0 < d < 100000 else None
    except (InvalidOperation, ValueError):
        return None

def normalize(payload, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows, seen = [], set()
    for p in payload['products']:
        if p.get('campaignID') != 16143: raise ValueError('Unexpected campaign')
        link = p['URL']; u = urlsplit(link); q = parse_qs(u.query)
        if u.scheme != 'https' or u.netloc != 'tc.tradetracker.net' or q.get('c') != ['16143'] or q.get('a') != ['518044']:
            raise ValueError('Unexpected tracking URL')
        dest = q.get('u', [''])[0]; target = urlsplit(dest)
        variant = parse_qs(target.query).get('variant', [''])[0]
        if target.scheme != 'https' or target.netloc != 'www.bauzaar.it' or not target.path.startswith('/products/') or not variant.isdigit():
            raise ValueError('Exact merchant variant required')
        if variant in seen: raise ValueError('Duplicate variant')
        seen.add(variant)
        props = p.get('properties', {}); stock = value(props, 'availability')
        if stock not in ('in stock', 'out of stock', 'preorder', 'backorder'): raise ValueError('Unknown availability')
        price = p['price']
        if price.get('currency') != 'EUR': raise ValueError('Unexpected currency')
        regular = amount(price['amount'])
        # A malformed/zero-priced row must not freeze every other merchant offer.
        # The all-invalid feed still fails closed below.
        if regular is None: continue
        current = regular
        sale = amount(value(props, 'sale_price')); period = value(props, 'sale_price_effective_date')
        if sale and sale < regular and period:
            start, end = (dt.datetime.fromisoformat(s.replace('Z', '+00:00')) for s in period.split('/'))
            if start.tzinfo is None or end.tzinfo is None: raise ValueError('Sale timezone required')
            if start <= now <= end: current = sale
        # unit_pricing_measure is the declared selling quantity, never delivery weight.
        measure = value(props, 'unit_pricing_measure')
        m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*(kg|g)', measure, re.I)
        kg = float(m[1].replace(',', '.')) / (1000 if m[2].lower() == 'g' else 1) if m else None
        if kg is not None and not 0 < kg <= 1000: kg = None
        # Do not syndicate coupon claims or unrelated category suffixes in feed titles.
        title = p['name'].split(' - 1° ORDINE?')[0].strip()
        title = title.replace(' - Croccantini per cani - Croccantini per gatti', '')
        if not title: raise ValueError('Missing title')
        images = p.get('images', [])
        rows.append(dict(id='bauzaar:'+variant, merchant='Bauzaar', merchant_id='bauzaar',
            title=title, variant=measure, feed_unit_pricing_measure=measure, brand=value(props, 'brand'), category=value(props, 'product_type'),
            price=current, previous_price=None, available=stock=='in stock', url=dest,
            affiliate_url=link, image=images[0] if images else '', sku='', gtin=value(props, 'GTIN'), feed_gtin=value(props, 'GTIN'),
            weight_kg=kg, weight_source='official_feed:unit_pricing_measure' if kg else '', shipping_weight_kg=None,
            checked_at=now.isoformat(), source_type='official_feed', image_source=feed_image(images[0] if images else '',16143,600171)))
        if current<regular:rows[-1]=with_reference(rows[-1],regular,'feed_regular_price',end.isoformat())
    if not rows: raise ValueError('Empty feed')
    return rows

def collect():
    now = dt.datetime.now(dt.timezone.utc)
    req = urllib.request.Request(FEED_URL, headers={'User-Agent':'Offerte4Zampe/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read(40_000_001)
        if len(raw) > 40_000_000: raise ValueError('Feed too large')
        last_modified = response.headers.get('Last-Modified')
    payload = json.loads(raw)
    rows = normalize(payload, now)
    excluded_invalid_prices = sum(amount(p.get('price', {}).get('amount')) is None for p in payload['products'])
    return rows, dict(id='bauzaar', name='Bauzaar', status='ok', checked_at=now.isoformat(), offers=len(rows),
        excluded_invalid_prices=excluded_invalid_prices, source='TradeTracker:600171', method='Feed ufficiale TradeTracker · aggiornamento giornaliero',
        retrieved_at=now.isoformat(), upstream_last_modified=last_modified)
