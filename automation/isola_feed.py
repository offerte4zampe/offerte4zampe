"""Approved Isola dei Tesori TradeTracker feed; exact product destinations only."""
try:
    from .matching_evidence import attach_description
except ImportError:
    from matching_evidence import attach_description

import datetime as dt
import html
import json
import re
import urllib.request
from urllib.parse import urlsplit, parse_qs
try:
    from .bauzaar_feed import amount, value
except ImportError:
    from bauzaar_feed import amount, value

try:
    from automation.image_policy import feed_image
except ImportError:
    from image_policy import feed_image

FEED_URL = 'https://pf.tradetracker.net/?aid=518044&encoding=utf-8&type=json&fid=1618255&categoryType=2&additionalType=2'

def normalize(payload, now=None, stats=None):
    try:
        from .update_catalog import weight
    except ImportError:
        from update_catalog import weight
    now = now or dt.datetime.now(dt.timezone.utc)
    rows, seen = [], set()
    for p in payload['products']:
        ident = str(p.get('ID', ''))
        if p.get('campaignID') != 31221 or not ident.isdigit() or ident in seen:
            raise ValueError('Unexpected campaign or duplicate product')
        seen.add(ident)
        link = p['URL']; u = urlsplit(link); q = parse_qs(u.query)
        if u.scheme != 'https' or u.netloc != 'tc.tradetracker.net' or q.get('c') != ['31221'] or q.get('a') != ['518044']:
            raise ValueError('Unexpected tracking URL')
        dest = q.get('u', [''])[0]; target = urlsplit(dest)
        if target.scheme != 'https' or target.netloc != 'www.isoladeitesori.it' or not re.fullmatch(r'/prodotto/[^/]+/'+re.escape(ident)+r'\.html', target.path) or target.fragment:
            raise ValueError('Exact merchant product required')
        # Feed titles/GTIN describe one unit but destination may request a multipack.
        # Exclude these until price/quantity semantics are verified with the merchant.
        if target.query:
            if re.fullmatch(r'multipack=\d+', target.query): continue
            raise ValueError('Unexpected destination parameters')
        if p.get('variations'): raise ValueError('Unmapped variants')
        props = p.get('properties', {}); stock = value(props, 'availability')
        if stock not in ('in_stock', 'out_of_stock', 'preorder', 'backorder'):
            if stats is not None:
                stats['excluded_unknown_availability'] = stats.get('excluded_unknown_availability', 0) + 1
            continue
        price = p['price']; current = amount(price.get('amount'))
        if price.get('currency') != 'EUR' or current is None: raise ValueError('Invalid EUR price')
        title = html.unescape(p['name']).strip()
        if not title: raise ValueError('Missing title')
        # Only explicit title package quantities; never deliveryCosts or transport weight.
        label = re.sub(r'\bgr\b', 'g', title, flags=re.I)
        kg = weight(label)
        if kg is not None and not 0 < kg <= 1000: kg = None
        images = p.get('images', [])
        rows.append(dict(id='isola-dei-tesori:'+ident, merchant='Isola dei Tesori', merchant_id='isola-dei-tesori',
            title=title, variant='', brand=html.unescape(value(props, 'brand')), category=value(props, 'product_type'),
            price=current, previous_price=None, available=stock=='in_stock', url=dest,
            affiliate_url=link, image=images[0] if images else '', sku='', gtin=value(props, 'GTIN'), feed_gtin=value(props, 'GTIN'),
            weight_kg=kg, weight_source='official_feed:title' if kg else '', shipping_weight_kg=None,
            checked_at=now.isoformat(), source_type='official_feed', image_source=feed_image(images[0] if images else '',31221,1618255)))
        attach_description(rows[-1],p.get('description',''))
    if not rows: raise ValueError('Empty feed')
    return rows


def feed_schema_counts(payload):
    """Only field names and aggregate presence/fill frequencies; no values."""
    try:
        products = payload.get('products', []) if isinstance(payload, dict) else []
        if not isinstance(products, list):
            return {'records': 0, 'fields': [], 'identifier_fields': []}
        counters = {}
        def register(key, value):
            if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', key):
                return
            if key not in counters:
                counters[key] = {'present': 0, 'filled': 0}
            counters[key]['present'] += 1
            if value is not None and value != '' and value != [] and value != {}:
                counters[key]['filled'] += 1
        for item in products:
            if not isinstance(item, dict):
                continue
            for key, val in item.items():
                register(key, val)
                if key == 'properties' and isinstance(val, dict):
                    for subkey, subvalue in val.items():
                        if isinstance(subkey, str):
                            register('properties.' + subkey, subvalue)
        fields = [{'key': k, 'present': v['present'], 'filled': v['filled'], 'total': len(products)}
                  for k, v in sorted(counters.items())]
        identifiers = [k for k in sorted(counters) if re.search(r'(?:^|[._-])(?:eans?|gtin|upc|isbn|mpn|skus?|barcodes?|product_?codes?)(?:$|[._-])', k, re.I)]
        return {'records': len(products), 'fields': fields, 'identifier_fields': identifiers}
    except Exception:
        return {'records': 0, 'fields': [], 'identifier_fields': []}


def log_feed_schema(payload):
    """Non-critical, log-only diagnostics; never change feed processing."""
    try:
        import logging
        logging.getLogger(__name__).warning('ISOLA_FEED_SCHEMA %s', json.dumps(feed_schema_counts(payload), ensure_ascii=True, separators=(',', ':')))
    except Exception:
        pass

def collect():
    now = dt.datetime.now(dt.timezone.utc)
    req = urllib.request.Request(FEED_URL, headers={'User-Agent':'Offerte4Zampe/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read(40_000_001)
        if len(raw) > 40_000_000: raise ValueError('Feed too large')
        last_modified = response.headers.get('Last-Modified')
    payload = json.loads(raw)
    log_feed_schema(payload)
    stats = {}
    rows = normalize(payload, now, stats)
    return rows, dict(id='isola-dei-tesori', name='Isola dei Tesori', status='ok', checked_at=now.isoformat(), offers=len(rows), excluded_unverified_quantity=len(payload['products'])-len(rows)-stats.get('excluded_unknown_availability', 0),
        excluded_unknown_availability=stats.get('excluded_unknown_availability', 0),
        source='TradeTracker:1618255', method='Feed ufficiale TradeTracker · aggiornamento giornaliero',
        retrieved_at=now.isoformat(), upstream_last_modified=last_modified)
