"""Build a small home payload from the final catalog, without changing prices."""
import collections
import hashlib
import math
import datetime
import gzip
import os
import json
import pathlib
import re


try:
    from automation.report_link import error_link
    from automation.product_link import product_url
except ImportError:
    from report_link import error_link
    from product_link import product_url

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(catalog, now=None, history=None):
    try:
        from .merchant_promotions import annotate
    except ImportError:
        from merchant_promotions import annotate
    catalog={**catalog,'offers':[annotate(o) for o in catalog['offers']]}
    now = now or datetime.datetime.now(datetime.timezone.utc)
    counts_by_store = collections.Counter(o.get('merchant_id') for o in catalog['offers'])
    catalog = {**catalog, 'sources': [{**s, 'offers': counts_by_store[s['id']]} for s in catalog['sources']]}
    def recent(o):
        try:
            return 0 <= (now - datetime.datetime.fromisoformat(o['checked_at'].replace('Z', '+00:00'))).total_seconds() <= 12 * 3600
        except (ValueError, KeyError, TypeError):
            return False
    # Current prices, independent of unverified comparison prices or commissions.
    def home_topic(o):
        title = o.get('title', '')
        if len(title) > 180 or re.search(r'\b(ricambi?o?|elastici)\b', title, re.I):
            return False
        label = title+' '+o.get('category', '')
        return bool(re.search(r'\b(cani|gatti|cane|gatto|dog|cat|crocchette|umido|food|tiragraffi|lettiera)\b', label, re.I)) and not re.search(r'integrator|veterinar|diabet|renal|medicat|diete vet|calmant|antiansia|antiparassitar|feromon|farmac', label, re.I)
    rows = [o for o in catalog['offers'] if str(o.get('url','')).startswith('https://') and o.get('available') and isinstance(o.get('price'), (int, float)) and o['price'] > 0 and home_topic(o)]
    # Rank from observed price history, not merchant 'previous_price' metadata.
    # Rotate the remaining fresh prices by UTC date to avoid an alphabetical homepage.
    today = now.date()
    sources = {s['id']: s for s in catalog.get('sources', [])}
    def valid(o):
        if not recent(o) or not o.get('image'):
            return False
        source = sources.get(o.get('merchant_id'), {})
        if source.get('status', 'ok') != 'ok':
            return False
        if source.get('checked_at'):
            try:
                stamp = datetime.datetime.fromisoformat(source['checked_at'].replace('Z', '+00:00'))
                if not 0 <= (now-stamp).total_seconds() <= 12*3600:
                    return False
            except (ValueError, TypeError):
                return False
        return True
    def rotate(o):
        return hashlib.sha256((today.isoformat() + ':' + o['id']).encode()).hexdigest()
    history_rows = (history or {}).get('offers', {}) if os.environ.get('PRICE_TRACKING_ENABLED','false').lower() == 'true' else {}
    candidates = []
    for original in rows:
        if not valid(original):
            continue
        o = dict(original)
        past = []
        for entry in history_rows.get(o['id'], []):
            try:
                day = datetime.date.fromisoformat(entry['day'])
                value = entry['last']
                if 0 < (today-day).days <= 30 and type(value) in (float, int) and math.isfinite(value) and value > 0:
                    past.append(value)
            except (ValueError, TypeError, KeyError):
                continue
        # Same SKU, at least two previous dated observations, compared to the
        # *lowest* older price. 5% minimum drop. No fabricated strike-through.
        if len(past) >= 2:
            baseline = min(past)
            percent = (baseline-o['price']) * 100 / baseline
            if percent >= 5:
                o['verified_before_price'] = round(baseline, 2)
                o['verified_discount_pct'] = round(percent, 1)
        candidates.append(o)
    # Compare only genuinely identical, GTIN/quantity-verified product groups.
    # The reference is the NEXT cheapest other merchant, not a list/MSRP price.
    # This is a cross-store saving, NEVER a retailer price reduction.
    groups = collections.defaultdict(list)
    for o in candidates:
        if o.get('product_identity_verified') is True and o.get('product_id'):
            groups[o['product_id']].append(o)
    for group in groups.values():
        cheapest_by_shop = {}
        for o in group:
            shop = o['merchant_id']
            if shop not in cheapest_by_shop or o['price'] < cheapest_by_shop[shop]['price']:
                cheapest_by_shop[shop] = o
        ordered = sorted(cheapest_by_shop.values(), key=lambda o: (o['price'], o['id']))
        if len(ordered) < 2:
            continue
        best, next_shop = ordered[:2]
        if best['price'] >= next_shop['price']:
            continue
        saving = (next_shop['price'] - best['price']) / next_shop['price'] * 100
        if saving >= 5 and next_shop['price'] - best['price'] >= 0.5:
            best['comparison_other_price'] = round(next_shop['price'], 2)
            best['comparison_savings_pct'] = round(saving, 1)
            best['comparison_savings_eur'] = round(next_shop['price']-best['price'], 2)
            best['comparison_other_merchant'] = next_shop['merchant']
    candidates.sort(key=lambda o: (0 if 'verified_discount_pct' in o
                                   else 1 if 'comparison_savings_pct' in o else 2,
                                   -o.get('verified_discount_pct', o.get('comparison_savings_pct', 0)),
                                   rotate(o)))
    selected, brands, shops = [], set(), collections.Counter()
    for o in candidates:
        brand = str(o.get('brand') or o.get('title') or o['id']).casefold()
        shop = o['merchant_id']
        if brand in brands or shops[shop] >= 8:
            continue
        selected.append(o)
        brands.add(brand)
        shops[shop] += 1
        if len(selected) >= 42:
            break
    spotlight_pool = [o for o in selected if 'verified_discount_pct' in o or 'comparison_savings_pct' in o][:3]
    daily_pick_id = spotlight_pool[today.toordinal() % len(spotlight_pool)]['id'] if spotlight_pool else None
    counts = collections.Counter(o['brand'] for o in rows if o.get('brand'))
    fields = ['id', 'title', 'merchant', 'merchant_id', 'brand', 'variant', 'price', 'weight_kg', 'image', 'image_local', 'url', 'affiliate_url', 'available', 'checked_at', 'canonical_title', 'canonical_format', 'canonical_shop_count', 'product_slug', 'product_url', 'unit_price', 'unit_price_unit', 'verified_before_price', 'verified_discount_pct', 'comparison_other_price', 'comparison_savings_pct', 'comparison_savings_eur', 'comparison_other_merchant', 'merchant_promotion', 'quantity_verified', 'weight_conflict']
    return {k: catalog[k] for k in ['generated_at', 'refresh_hours', 'sources']} | {
        'stats': {'offers': len(catalog['offers']), 'brands': len({o.get('brand') for o in catalog['offers'] if o.get('brand')})},
        'top_brands': [brand for brand, count in counts.most_common(10)],
        'daily_pick_id': daily_pick_id,
        'offers': [{k: o[k] for k in fields if k in o} for o in selected],
    }




def telegram_picks(catalog, now=None, limit=180):
    """Separate, bounded feed of fresh product photos from approved partner catalogs."""
    from urllib.parse import urlparse
    now = now or datetime.datetime.now(datetime.timezone.utc)
    hosts = {'isola-dei-tesori': 'www.isoladeitesori.it', 'paco': 'www.pacopetshop.it'}
    sources = {s['id']: s for s in catalog.get('sources', []) if s.get('id') in hosts and s.get('status') == 'ok'}
    def fresh(value):
        try:
            age = (now - datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))).total_seconds()
            return 0 <= age <= 12 * 3600
        except (ValueError, KeyError, TypeError, AttributeError):
            return False
    groups = {merchant: [] for merchant in hosts}
    for o in catalog.get('offers', []):
        merchant = o.get('merchant_id')
        source = sources.get(merchant)
        if not source or not fresh(source.get('checked_at')) or not fresh(o.get('checked_at')):
            continue
        title = o.get('title')
        if not isinstance(title, str) or not (5 <= len(title.strip()) <= 160):
            continue
        label = title + ' ' + str(o.get('category') or '')
        if not re.search(r'\b(cane|cani|gatto|gatti|dog|cat|crocchette|umido|snack|lettiera)\b', label, re.I):
            continue
        if re.search(r'integrator|veterinar|diabet|renal|medicat|diete vet|calmant|antiansia|antiparassitar|feromon|farmac', label, re.I):
            continue
        price, weight = o.get('price'), o.get('weight_kg')
        if o.get('available') is not True or type(price) not in (int, float) or not (0 < price < 10000) or type(weight) not in (int, float) or not (0 < weight < 1000):
            continue
        variant = o.get('variant') or o.get('canonical_format') or ''
        if not variant and not re.search(r'\d+(?:[.,]\d+)?\s*(?:kg|g|gr|grammi|ml|l)\b', title, re.I):
            continue
        image = o.get('image')
        if not isinstance(image, str):
            continue
        parsed = urlparse(image)
        if parsed.scheme != 'https' or parsed.hostname != hosts[merchant] or parsed.username or parsed.password or not re.search(r'\.(?:jpe?g|png)$', parsed.path, re.I):
            continue
        groups[merchant].append(o)
    fields = ('id', 'title', 'merchant', 'merchant_id', 'brand', 'variant', 'canonical_format', 'price', 'weight_kg', 'image', 'available', 'checked_at', 'product_url')
    for merchant in groups:
        groups[merchant].sort(key=lambda o: (str(o.get('brand') or '').casefold(), o['title'].casefold(), o['id']))
    chosen, brands = [], collections.Counter()
    while len(chosen) < limit and any(groups.values()):
        progress = False
        for merchant in groups:
            for index, o in enumerate(groups[merchant]):
                brand = str(o.get('brand') or '').casefold()
                if brands[brand] < 5:
                    chosen.append({k: o[k] for k in fields if k in o})
                    brands[brand] += 1
                    groups[merchant].pop(index)
                    progress = True
                    break
            if len(chosen) >= limit:
                break
        if not progress:
            break
    return {'generated_at': catalog.get('generated_at'), 'sources': list(sources.values()), 'offers': chosen}



def search_index(catalog):
    """Only names and provenance for suggestions: no prices, images or tracking URLs."""
    fields = ('id', 'title', 'variant', 'brand', 'gtin', 'merchant', 'available', 'checked_at', 'product_slug', 'product_url')
    return {'generated_at': catalog.get('generated_at'), 'offers': [
        {key: offer[key] for key in fields if key in offer}
        for offer in catalog.get('offers', []) if isinstance(offer.get('title'), str)
    ]}


def main():
    data = json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    path = ROOT/'site/data/home.json'
    index = ROOT/'site/data/search-index.json'
    index.write_text(json.dumps(search_index(data), ensure_ascii=False, separators=(',', ':'))+'\n')
    print(f'Search index: {index.stat().st_size} bytes; gzip {len(gzip.compress(index.read_bytes()))} bytes')
    picks_path = ROOT/'site/data/telegram-picks.json'
    picks_path.write_text(json.dumps(telegram_picks(data), ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Telegram picks: {picks_path.stat().st_size} bytes')
    history_path = ROOT/'site/data/price-history.json.gz'
    history = json.loads(gzip.decompress(history_path.read_bytes())) if history_path.exists() else {}
    payload = build(data, history=history)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    home = ROOT/'site/index.html'
    home.write_text(render_home(home.read_text(), payload))
    print(f'Home payload: {path.stat().st_size} bytes')



def pick(payload):
    """Same source diversity and distinct-brand order for HTML and hydration."""
    # This is the *offers* section: a plain current price is not an offer.
    sales = [o for o in payload['offers'] if
             'verified_discount_pct' in o or 'comparison_savings_pct' in o]
    picked, brands = [], set()
    for o in sales:
        if len(picked) >= 6:
            break
        brand = o.get('brand')
        if brand not in brands:
            picked.append(o)
            brands.add(brand)
    hero = next((o for o in picked if o['id'] == payload.get('daily_pick_id')), None)
    return picked, (hero or (picked[0] if picked else None))


def replace_region(html, element_id, content):
    import re
    opening = re.search(r'<(div|p)\b[^>]*\bid="'+re.escape(element_id)+r'"[^>]*>', html)
    if not opening:
        raise ValueError('Missing home region: '+element_id)
    depth = 1
    for token in re.finditer(r'</?'+opening[1]+r'\b[^>]*>', html[opening.end():]):
        depth += -1 if token[0].startswith('</') else 1
        if not depth:
            end = opening.end()+token.start()
            return html[:opening.end()]+content+html[end:]
    raise ValueError('Unclosed home region: '+element_id)


def render_home(html, payload):
    # Fail closed even when a stale pre-generated home payload is supplied.
    if os.environ.get('PRICE_TRACKING_ENABLED','false').lower() != 'true':
        payload = {**payload, 'offers': [
            {k:v for k,v in item.items() if k not in ('verified_before_price','verified_discount_pct')}
            for item in payload.get('offers', [])
        ]}
    from html import escape as h, unescape
    from urllib.parse import urlencode
    import re
    def money(value):
        return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')+' €'
    region = re.search(r'<div\b[^>]*\bid="home-brands"[^>]*>', html)
    mapping = re.search(r'data-brand-pages="([^"]*)"', region[0]) if region else None
    try:
        brand_pages = json.loads(unescape(mapping[1])) if mapping else {}
    except (ValueError, TypeError):
        brand_pages = {}
    def link(label, **params):
        target = brand_pages.get(params.get('brand'))
        if isinstance(target, str) and re.fullmatch(r'/marca-[a-z0-9-]+', target):
            return f'<a href="{h(target, quote=True)}">{h(label)}</a>'
        return f'<a href="confronta-cibo.html?{h(urlencode(params), quote=True)}">{h(label)}</a>'
    try:
        from .merchant_promotions import render as render_promotion
    except ImportError:
        from merchant_promotions import render as render_promotion
    def card(o, spotlight=False):
        tag = 'h3'
        image = o.get('image', '')
        img = f'<img src="{h(image,quote=True)}" alt="" width="160" height="145" loading="lazy">' if image.startswith('https://') else ''
        unit = f'<p class="micro">{money(o["price"]/o["weight_kg"])}/kg</p>' if o.get('weight_kg') else ''
        title = o.get('canonical_title') or o['title']
        cta = 'Vedi offerta →' if o.get('canonical_shop_count', 2) < 2 else 'Confronta nei negozi →'
        if o.get('unit_price') and o.get('unit_price_unit'):
            unit = '<p class="micro">'+money(o['unit_price'])+'/'+h(o['unit_price_unit'])+'</p>'
        if 'verified_discount_pct' in o:
            evidence = ('<div class="price-evidence is-drop"><span class="savings-badge">−'
                        +h(str(o['verified_discount_pct']).replace('.', ','))+'% RIBASSO</span>'
                        +'<p class="price-before">Prima <del>'+money(o['verified_before_price'])+'</del></p>'
                        +'<p class="price-proof-note">Prezzo precedente osservato sulla stessa offerta</p></div>')
        elif 'comparison_savings_pct' in o:
            evidence = ('<div class="price-evidence is-comparison"><span class="savings-badge">−'
                        +h(str(o['comparison_savings_pct']).replace('.', ','))+'% TRA NEGOZI</span>'
                        +'<p class="price-before">Altrove '+money(o['comparison_other_price'])+'</p>'
                        +'<p class="price-proof-note">Confronto sullo stesso prodotto con '
                        +h(o['comparison_other_merchant'])+' · non è uno sconto del negozio</p></div>')
        else:
            evidence = '<p class="micro price-no-discount">Prezzo aggiornato · nessuno sconto verificato</p>'
        return f'''<article class="{'spotlight-product' if spotlight else 'home-deal'}{' has-price-proof' if ('verified_discount_pct' in o or 'comparison_savings_pct' in o) else ''}" data-home-offer="{h(o['checked_at'],quote=True)}">{img}<p class="micro">{h(o['merchant'])} · {h(o['brand'])}</p><{tag}><a class="product-title-link" href="{h(product_url(o),quote=True)}">{h(title)}</a></{tag}><p class="micro">{h(o.get('variant') or '')}</p><p class="catalog-price"><span class="price-now-label">Qui</span><strong>{money(o['price'])}</strong></p>{evidence}{render_promotion(o)}{unit}<p class="micro">Rilevato: <time datetime="{h(o['checked_at'],quote=True)}">{h(o['checked_at'][:16].replace('T',' '))} UTC</time></p><a class="btn secondary" href="{h(product_url(o),quote=True)}">{cta}</a>{error_link(o)}</article>'''
    deals, hero = pick(payload)
    parts = {
        'home-deals': ''.join(card(o) for o in deals) if deals else '<p class="home-no-proof">Oggi non risultano ribassi o risparmi tra negozi sufficientemente verificati. <a href="/confronta-cibo">Confronta comunque i prezzi aggiornati →</a></p>',
        'home-spotlight': '<h2 class="sr-only">Risparmio verificato in evidenza</h2>'+card(hero, True) if hero else '<p class="micro">Nessun risparmio verificato al momento. <a href="/confronta-cibo">Esplora i prezzi rilevati →</a></p>',
        'home-deals-status': 'Catalogo aggiornato il '+h(payload['generated_at'][:16].replace('T',' '))+' UTC. '+(str(sum('verified_discount_pct' in o for o in deals))+' ribassi storici verificati, ' if os.environ.get('PRICE_TRACKING_ENABLED','false').lower() == 'true' else '')+str(sum('comparison_savings_pct' in o and 'verified_discount_pct' not in o for o in deals))+' risparmi tra negozi verificati nella selezione. In questa sezione non pubblichiamo prezzi senza prova di risparmio. Spedizione esclusa.',
        'home-stats': ''.join('<span>'+h(s)+'</span>' for s in [f"{payload['stats']['offers']:,}".replace(',', '.')+' offerte importate', str(payload['stats']['brands'])+' marche', str(sum(s.get('offers',0)>0 for s in payload['sources']))+' negozi', 'Verifiche programmate ogni '+str(payload['refresh_hours'])+' ore']),
        'home-brands': ''.join(link(brand, brand=brand) for brand in payload['top_brands']),
        'home-shops': ''.join(link(s['name']+' · '+str(s['offers'])+' offerte →', shop=s['name']) for s in payload['sources'] if s.get('offers',0)>0),
    }
    for element_id, content in parts.items():
        html = replace_region(html, element_id, content)
    # Match the promotion heading to the evidence actually available.
    heading = 'OFFERTA DEL GIORNO' if hero else 'NESSUNA OFFERTA VERIFICATA OGGI'
    html = re.sub(r'(<span\b[^>]*\bid="daily-pick-label"[^>]*>)[^<]*(</span>)',
                  lambda m: m[1] + heading + m[2], html, count=1)
    # Keep both SEO descriptions aligned with the actual imported shops, not a stale static list.
    shops = [s['name'] for s in payload['sources'] if s.get('offers', 0) > 0 and s.get('name')]
    if shops:
        shop_names = ', '.join(shops[:-1]) + (' e ' if len(shops) > 1 else '') + shops[-1]
        summary = f'Confronta offerte e prezzi per cani e gatti da {shop_names}. Prezzi rilevati, non in tempo reale.'
        html = re.sub(r'(<meta\s+(?:name="description"|property="og:description")\s+content=")[^"]*(">)',
                      lambda m: m[1] + h(summary, quote=True) + m[2], html)
    html = re.sub(r'(<main\b[^>]*?)(?: data-home-generated="[^"]*")?(>)', lambda m: re.sub(r' data-home-generated="[^"]*"', '', m[1])+' data-home-generated="'+h(payload['generated_at'],quote=True)+'"'+m[2], html, count=1)
    return html


if __name__ == '__main__':
    main()
