"""Curated brand landing pages backed by exact catalog brand labels."""
import gzip
import json
from pathlib import Path
from html import escape as h
from urllib.parse import urlencode
import re
try:
    from .brand_landings import brand_pages, legacy_brand_pages, canonical_brand, in_scope
    from .product_link import product_url
    from .freshness import label as freshness_label
except ImportError:
    from brand_landings import brand_pages, legacy_brand_pages, canonical_brand, in_scope
    from product_link import product_url
    from freshness import label as freshness_label
try:
    from .build_product_pages import page, fresh
    from .build_matched_pages import groups, slug_for, product_label, merchant_url
except ImportError:
    from build_product_pages import page, fresh
    from build_matched_pages import groups, slug_for, product_label, merchant_url

try:
    from automation.list_schema import append_list_schema
except ImportError:
    from list_schema import append_list_schema


try:
    from automation.report_link import error_link
except ImportError:
    from report_link import error_link

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://offerte4zampe.it/'
BRANDS = [('monge','Monge'),('royal-canin','Royal Canin'),('farmina','Farmina'),('natural-trainer','Natural Trainer'),('purina-pro-plan','Purina Pro Plan')]


def money(value):
    return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')+' €'

def select(offers, brand, limit=24):
    rows = [o for o in offers if in_scope(o) and canonical_brand(o.get('brand','')).casefold()==brand.casefold() and fresh(o) and o.get('available') and o.get('price',0)>0 and str(o.get('url','')).startswith('https://')]
    # Alphabetical source rotation is an editorial sample, never a price ranking.
    byshop = {shop:sorted([o for o in rows if o['merchant']==shop],key=lambda o:(product_label(o).casefold(),o['id'])) for shop in sorted({o['merchant'] for o in rows})}
    picked = []
    while len(picked)<limit and any(byshop.values()):
        for shop in byshop:
            if byshop[shop] and len(picked)<limit:
                picked.append(byshop[shop].pop(0))
    return rows,picked


def build():
    offers = json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))['offers']
    template = (ROOT/'site/chi-siamo.html').read_text()
    matched = groups(offers)
    commercial_path = ROOT/'site/data/commercial-lines.json'
    commercial_lines = json.loads(commercial_path.read_text()).get('active', []) if commercial_path.exists() else []
    canonical = {name:'/marca-'+slug for slug,name in brand_pages(offers) if len(select(offers,name)[0])>=5}
    legacy = {name:'/marca-'+slug for slug,name in legacy_brand_pages(offers)}
    prior_path = ROOT/'site/data/brand-pages.json'
    if prior_path.exists(): legacy.update(json.loads(prior_path.read_text()))
    redirect_path = ROOT/'site/data/brand-redirects.json'
    redirects = json.loads(redirect_path.read_text()) if redirect_path.exists() else {}
    for name,old in legacy.items():
        target = canonical.get(canonical_brand(name))
        if target and old != target: redirects[old] = target
    # Only one-hop local redirects, never loops or stale destinations.
    redirects = {old:target for old,target in redirects.items() if target in canonical.values() and old not in canonical.values()}
    redirect_path.write_text(json.dumps(redirects,ensure_ascii=False,separators=(',',':'))+'\n')
    links, list_items, active_slugs = [], [], set()
    for suffix,brand in brand_pages(offers):
        slug = 'marca-'+suffix
        rows,picked = select(offers,brand)
        if len(rows)<5:
            if (ROOT/f'site/{slug}.html').exists():
                body = '<section class="pagehero"><div class="wrap"><h1>'+h(brand)+': catalogo da aggiornare</h1><p>Non ci sono dati recenti sufficienti per questa selezione.</p><a href="confronta-cibo.html">Cerca nel catalogo →</a></div></section>'
                (ROOT/f'site/{slug}.html').write_text(page(template,slug,brand+': dati da aggiornare','Dati recenti non sufficienti.',body).replace('content="index,follow"','content="noindex,follow"'))
            continue
        active_slugs.add(slug)
        cards,items = [],[]
        for i,o in enumerate(picked):
            key=(o.get('gtin'),format(o['weight_kg'],'.12g'),o['brand'].strip().lower()) if o.get('weight_kg') else None
            comparison = slug_for(key) if key in matched else None
            if comparison and not (ROOT/f'site/{comparison}.html').exists(): comparison=None
            more = f'<a href="{comparison}.html">Stesso codice e formato in più negozi →</a>' if comparison else ''
            unit = money(o['price']/o['weight_kg'])+'/kg' if o.get('weight_kg') else 'Peso netto non verificato: prezzo/kg non calcolato'
            rel = 'sponsored noopener noreferrer' if o.get('affiliate_url') else 'noopener noreferrer'
            disclosure = '<p class="micro">Possiamo ricevere una commissione, senza costi aggiuntivi per te.</p>' if o.get('affiliate_url') else ''
            label = product_label(o)
            warning = '<p class="notice">'+h(freshness_label(o["checked_at"]))+'</p>' if freshness_label(o["checked_at"]) else ''
            cards.append(f'<article class="catalog-card"><p class="micro">{h(o["merchant"])} · {h(o["brand"])}</p><h3><a class="product-title-link" href="{h(product_url(o),quote=True)}">{h(label)}</a></h3><p>{h(o.get("variant") or "Formato non specificato")}</p><p class="catalog-price"><strong>{money(o['price'])}</strong></p><p>{unit} · spedizione esclusa</p><p class="micro">Disponibile al rilevamento · recupero dati: <time datetime="{h(o["checked_at"],quote=True)}">{h(o["checked_at"])}</time></p>{warning}{more}<a class="btn secondary" href="{h(product_url(o),quote=True)}">Vedi scheda →</a>{disclosure}{error_link(o)}</article>')
            items.append({'@type':'ListItem','position':i+1,'name':label,'url':BASE+comparison if comparison else product_url(o)})
        shop_count=len({o['merchant_id'] for o in rows})
        shops=str(shop_count)+(' negozio' if shop_count==1 else ' negozi')
        title=brand+': prodotti, formati e prezzi rilevati'
        query=h(urlencode({'brand':brand}),quote=True)
        body=f'<section class="pagehero"><div class="wrap"><nav aria-label="Percorso"><a href="index.html">Home</a> / <a href="marche.html">Marche</a></nav><h1>{h(title)}</h1><p>{len(rows)} offerte disponibili al rilevamento in {shops} del catalogo, {sum(bool(o.get("weight_kg")) for o in rows)} con peso netto dichiarato.</p></div></section><section class="section"><div class="wrap"><p class="notice">Questa pagina raggruppa la marca «{h(brand)}» e le sue etichette equivalenti nei cataloghi. Le linee e le ricette restano distinte nelle singole schede. Non è l’intero assortimento del produttore né una classifica di qualità. Prezzi rilevati, non in tempo reale; spedizione esclusa.</p><h2>Come leggere la selezione {h(brand)}</h2><p>Controlla nome completo, ricetta, fascia di età e formato. Prodotti della stessa marca non sono equivalenti: non confrontare automaticamente alimenti diversi usando soltanto il prezzo al kg. Per diete veterinarie e necessità nutrizionali segui le indicazioni del veterinario.</p><p>Mostriamo fino a 24 offerte, alternate per negozio e in ordine alfabetico all’interno di ogni fonte. Le commissioni non determinano la selezione. Quando codice GTIN, marca e peso netto coincidono, trovi un collegamento al confronto dello stesso formato.</p><a class="btn" href="/{slug}">Offerte {h(brand)} in questa selezione</a><div class="catalog-grid">'+''.join(cards)+'</div><h2>Strumenti utili prima di acquistare</h2><p><a href="/calcolatore#manual-tool">Confronta costo/kg e costo giornaliero</a> con la razione del produttore; <a href="calcolatore.html">organizza il budget</a> oppure leggi <a href="costo-crocchette-cane.html">come calcolare il costo mensile delle crocchette</a>.</p><p><a href="chi-siamo.html">Metodo e fonti</a> · <a href="marche.html">Altre marche del catalogo</a></p></div></section>'
        data={'@context':'https://schema.org','@graph':[{'@type':'ItemList','name':title,'itemListElement':items},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':BASE+url} for i,(name,url) in enumerate([('Home',''),('Marche','marche'),(brand,slug)])]}]}
        output=page(template,slug,title,brand+': '+str(len(rows))+' offerte rilevate in '+shops+'. Consulta schede, confezioni e prezzi; confronta i negozi sullo stesso prodotto. Spedizione esclusa.',body)
        if brand.casefold()=='bauzaar':
            output=output.replace('content="index,follow"','content="noindex,follow"')
        # Only link the commercial lines that passed the exact catalog gate.
        brand_lines = [line for line in commercial_lines if brand.casefold() in line['brands']]
        if brand_lines:
            line_links = '<section aria-label="Linee commerciali selezionate"><h2>Linee disponibili nel catalogo</h2><ul>' + ''.join(
                '<li><a href="/' + h(line['slug'], quote=True) + '">' + h(line['label']) + '</a></li>'
                for line in brand_lines
            ) + '</ul></section>'
            output = output.replace('<div class="catalog-grid">',line_links+'<div class="catalog-grid">',1)
        if brand=='Monge' and (ROOT/'site/linea-monge-bwild.html').exists():
            output=output.replace('<div class="catalog-grid">','<p><a href="linea-monge-bwild.html">Esplora la linea Monge BWild: ricette e formati distinti</a></p><div class="catalog-grid">',1)
        output=output.replace('</head>','<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script></head>')
        (ROOT/f'site/{slug}.html').write_text(output)
        list_items.append((brand,BASE+slug))
        links.append(f'<li><a href="{slug}.html">{h(brand)}</a> · {len(rows)} offerte rilevate · {shops}</li>')
    for old in (ROOT/'site').glob('marca-*.html'):
        if old.stem not in active_slugs:
            old.write_text(old.read_text().replace('content="index,follow"','content="noindex,follow"'))
    if (ROOT/'site/linea-monge-bwild.html').exists():
        links.append('<li><a href="linea-monge-bwild.html">Linea Monge BWild</a> · ricette e formati distinti</li>')
    for line in commercial_lines:
        links.append('<li><a href="/' + h(line['slug'], quote=True) + '">Linea ' + h(line['label']) + '</a> · formati e prezzi rilevati</li>')
    body='<section class="pagehero"><div class="wrap"><h1>Marche: trova i tuoi prodotti abituali</h1><p>Tutte le marche con almeno cinque offerte disponibili e recenti nei cataloghi. Ogni pagina distingue nomi, formati, fonti e data di recupero.</p></div></section><section class="section"><div class="wrap content"><ul>'+''.join(links)+'</ul><p>Le marche con meno di cinque offerte recenti restano disponibili nel comparatore. <a href="confronta-cibo.html">Usa il filtro marca nel comparatore</a> per esplorare il catalogo completo.</p></div></section>'
    (ROOT/'site/marche.html').write_text(append_list_schema(page(template,'marche','Marche di prodotti per animali: prezzi e formati','Marche con dati di catalogo sufficienti: ricette, confezioni, negozi e prezzi rilevati.',body),'Marche nel catalogo',list_items))
    home=ROOT/'site/index.html'
    before=home.read_text()
    if 'href="marche.html"' not in before and 'href="/marche"' not in before:
        before=before.replace('<div class="brand-links" id="home-brands">','<p><a href="marche.html">Esplora le pagine delle marche →</a></p><div class="brand-links" id="home-brands">')
        home.write_text(before)
    (ROOT/'site/data/brand-pages.json').write_text(json.dumps({name:'/marca-'+slug for slug,name in brand_pages(offers) if len(select(offers,name)[0])>=5},ensure_ascii=False,separators=(',',':')))
    print('Brand pages generated:',len(links))


if __name__ == '__main__':
    build()
