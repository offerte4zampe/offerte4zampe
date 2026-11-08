"""Curated commercial line SEO hubs generated only from fresh exact catalog evidence.

No fuzzy brand matching, no search-volume claims, no medicine lines or price history.
"""
import datetime as dt
import gzip
import json
import math
import re
from html import escape as h
from pathlib import Path

try:
    from automation.build_product_pages import page, fresh
    from automation.product_link import product_url
except ImportError:
    from build_product_pages import page, fresh
    from product_link import product_url

ROOT = Path(__file__).resolve().parents[1]
# Explicit editorial allowlist: never discover/publish unlimited line URLs.
# Each title token must match the actual merchant title, not a guessed synonym.
LINES = (
    ('monge-supreme', 'Monge Supreme', ('monge',), r'\\bsupreme\\b'),
    ('monge-monoprotein', 'Monge Monoprotein', ('monge',), r'\\bmonoprotein\\b'),
    ('royal-canin-sterilised', 'Royal Canin Sterilised', ('royal canin',), r'\\bsterili[sz]ed\\b'),
    ('royal-canin-mini-adult', 'Royal Canin Mini Adult', ('royal canin',), r'\\bmini\\s+adult\\b'),
    ('royal-canin-kitten', 'Royal Canin Kitten', ('royal canin',), r'\\bkitten\\b'),
    ('farmina-vet-life', 'Farmina Vet Life', ('farmina',), r'\\bvet\\s+life\\b'),
    ('farmina-nd', 'Farmina N&D', ('farmina',), r'\\bn\\s*&\\s*d\\b|\\bn\\s+and\\s+d\\b'),
    ('natural-trainer-sterilised', 'Natural Trainer Sterilised', ('natural trainer','trainer'), r'\\bsterili[sz]ed\\b'),
    ('gourmet-gold', 'Gourmet Gold', ('gourmet',), r'\\bgold\\b'),
    ('gourmet-perle', 'Gourmet Perle', ('gourmet',), r'\\bperle\\b'),
    ('almo-nature-hfc', 'Almo Nature HFC', ('almo nature',), r'\\bhfc\\b'),
    ('biokats-bianco', "Biokat's Bianco", ("biokat's", 'biokats'), r'\\bbianco\\b'),
    ('purina-pro-plan', 'Purina Pro Plan', ('purina pro plan',), r'\\bpro\\s+plan\\b'),
    ('acana-adult', 'Acana Adult', ('acana',), r'\\badult\\b'),
    ('hills-science-plan', "Hill's Science Plan", ("hill's science plan", "hill's"), r'\\bscience\\s+plan\\b'),
)
MIN_OFFERS = 12
MIN_MERCHANTS = 2
MIN_PRODUCTS = 4
MAX_CARDS = 24


def eligible(offer, brands, pattern, now=None):
    brand = str(offer.get('brand') or '').strip().casefold()
    title = str(offer.get('title') or '')
    price = offer.get('price')
    return (brand in brands
            and bool(re.search(pattern, title, re.I))
            and offer.get('available') is True
            and fresh(offer, now)
            and isinstance(price, (float, int)) and math.isfinite(price) and price > 0
            and product_url(offer).startswith('/prodotto/')
            and str(offer.get('url') or '').startswith('https://')
            and bool(offer.get('merchant_id')))


def select(offers, line, now=None):
    slug, label, brands, pattern = line
    rows = [o for o in offers if eligible(o, brands, pattern, now)]
    # Every listed product has a verified internal canonical slug; no inferred merging.
    count_products = len({product_url(o) for o in rows})
    count_merchants = len({o['merchant_id'] for o in rows})
    if len(rows) < MIN_OFFERS or count_merchants < MIN_MERCHANTS or count_products < MIN_PRODUCTS:
        return rows, []
    byshop = {shop: sorted((o for o in rows if o['merchant_id'] == shop),
                           key=lambda o: (o['title'].casefold(), o['id']))
              for shop in sorted({o['merchant_id'] for o in rows})}
    selected, used_products = [], set()
    while len(selected) < MAX_CARDS and any(byshop.values()):
        for shop in byshop:
            while byshop[shop]:
                item = byshop[shop].pop(0)
                target = product_url(item)
                if target not in used_products:
                    used_products.add(target)
                    selected.append(item)
                    break
            if len(selected) >= MAX_CARDS:
                break
    return rows, selected


def render(template, line, rows, selected):
    slug, label, brands, pattern = line
    shops = len({o['merchant_id'] for o in rows})
    intro = ('Questa selezione comprende solo offerte recenti con denominazione commerciale '
             'esplicita nel catalogo. Ricette, fasce di età e formati non sono intercambiabili. '
             'Prezzi e disponibilità sono rilevati, non in tempo reale.')
    cards = []
    for offer in selected:
        target = h(product_url(offer), quote=True)
        title = h(offer['title'])
        price = f"{offer['price']:.2f}".replace('.', ',')
        weight = offer.get('weight_kg')
        perkg = (f"{offer['price']/weight:.2f}".replace('.', ',') + ' €/kg'
                 if isinstance(weight, (float, int)) and math.isfinite(weight) and weight > 0
                 else 'Peso netto non verificato')
        cards.append(f'<article class="catalog-card"><h3><a href="{target}">{title}</a></h3>'
                     f'<p>{h(str(offer.get("variant") or "Formato da verificare"))}</p>'
                     f'<p>{h(str(offer.get("merchant") or offer["merchant_id"]))} · '
                     f'<strong>{price} €</strong> · {perkg} · spedizione esclusa</p>'
                     f'<p class="micro">Rilevato: <time datetime="{h(offer["checked_at"],quote=True)}">'
                     f'{h(offer["checked_at"][:10])}</time></p>'
                     f'<a class="btn secondary" href="{target}">Apri la scheda prodotto</a></article>')
    title = label + ': prodotti, formati e prezzi rilevati'
    body = ('<section class="pagehero"><div class="wrap"><nav aria-label="Percorso">'
            '<a href="/">Home</a> / <a href="/marche">Marche</a> / ' + h(label) +
            '</nav><h1>' + h(title) + '</h1><p>' + h(intro) + '</p></div></section>'
            '<section class="section"><div class="wrap content"><h2>Come confrontare questa linea</h2>'
            '<p>Verifica sempre nome completo, specie, variante, ricetta, peso netto e numero '
            'di pezzi. Confronta prezzi solo tra confezioni identiche. Non presentiamo '
            'una classifica di qualità né uno sconto comune a prodotti diversi.</p>'
            '<p>' + str(len(rows)) + ' offerte recenti rilevate in ' + str(shops) +
            ' negozi; ' + str(len({product_url(o) for o in rows})) +
            ' schede prodotto distinte. Qui mostriamo un campione di massimo 24 schede.</p>'
            '<div class="catalog-grid">' + ''.join(cards) + '</div>'
            '<h2>Metodo di selezione</h2><p>Includiamo solo le offerte con la marca '
            'indicata nel catalogo e la denominazione commerciale esatta nel titolo. '
            'L’assenza di un negozio non significa che non venda questa linea. '
            'I collegamenti portano alle schede del nostro comparatore, non a nuovi '
            'prodotti dedotti automaticamente dai nomi.</p>'
            '<p><a href="/marche">Esplora tutte le marche</a> · '
            '<a href="/chi-siamo">Metodo e affiliazioni</a></p></div></section>')
    return page(template, 'linea-' + slug, title,
                label + ': ricette, formati e prezzi osservati presso negozi diversi. Verifica le singole schede.',
                body)


def build(root=ROOT, now=None):
    catalog = json.loads(gzip.decompress((root/'site/data/catalog.json.gz').read_bytes()))
    template = (root/'site/chi-siamo.html').read_text()
    active, audit = [], []
    for line in LINES:
        slug, label, brands, pattern = line
        rows, selected = select(catalog['offers'], line, now)
        url = root/'site'/('linea-' + slug + '.html')
        audit.append({'slug': slug, 'offers': len(rows),
                      'merchants': len({o['merchant_id'] for o in rows}),
                      'products': len({product_url(o) for o in rows}), 'published': bool(selected)})
        if selected:
            url.write_text(render(template, line, rows, selected))
            active.append({'slug': 'linea-' + slug, 'label': label, 'brands': list(brands)})
        elif url.exists():
            # Preserve a previously discovered URL without publishing stale prices.
            url.write_text(page(template, 'linea-' + slug, label + ': catalogo da aggiornare',
                                'Dati recenti insufficienti; verifica nel catalogo.',
                                '<section class="pagehero"><div class="wrap"><h1>' + h(label) +
                                '</h1><p>Dati recenti insufficienti. Nessun prezzo storico '
                                'viene presentato come attuale.</p><a href="/confronta-cibo">'
                                'Cerca nel catalogo</a></div></section>').replace(
                                    'content="index,follow"', 'content="noindex,follow"'))
    (root/'site/data/commercial-lines.json').write_text(
        json.dumps({'active': active, 'audit': audit}, ensure_ascii=False, indent=2) + '\n')
    print('Commercial lines active:', len(active), 'of', len(LINES))
    return active


if __name__ == '__main__':
    build()
