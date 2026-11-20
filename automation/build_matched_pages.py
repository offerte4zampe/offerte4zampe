"""Static exact-format comparisons. No fuzzy recipe or package matching."""
import datetime
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from html import escape as h
from pathlib import Path
from urllib.parse import urlencode
try:
    from .build_product_pages import fresh, page
except ImportError:
    from build_product_pages import fresh, page


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

def product_label(offer):
    title = offer['title']
    variant = offer.get('variant') or ''
    if variant and variant.lower() not in ('default title','1ct') and variant.lower() not in title.lower():
        title += ' — '+variant
    return title


def merchant_url(offer):
    affiliate = offer.get('affiliate_url') or ''
    return affiliate if affiliate.startswith('https://') else offer['url']



def valid_gtin(code):
    return isinstance(code, str) and len(code) in (8,12,13,14) and code.isascii() and code.isdigit() and sum(int(n)*(3 if i%2==0 else 1) for i,n in enumerate(reversed(code[:-1]))) % 10 == (-int(code[-1])) % 10


def groups(offers):
    result = defaultdict(list)
    for o in offers:
        if o.get('comparison_review',{}).get('review_state')=='unverified':continue
        weight = o.get('weight_kg')
        if (valid_gtin(o.get('gtin')) and isinstance(weight,(int,float)) and math.isfinite(weight) and weight>0
            and o.get('brand','').strip() and fresh(o) and isinstance(o.get('price'),(int,float)) and math.isfinite(o['price']) and o['price']>0
            and str(o.get('url','')).startswith('https://')):
            result[(o['gtin'],format(weight,'.12g'),o['brand'].strip().lower())].append(o)
    return {key:rows for key,rows in result.items() if len({o['merchant_id'] for o in rows})>1}


def slug_for(key):
    return 'prezzi-'+key[0]+'-'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:10]


def structured_data(key, rows, slug):
    live = [o for o in rows if o['available']]
    crumbs = {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':BASE+url} for i,(name,url) in enumerate([('Home',''),('Confronti per prodotto','confronti-prodotti'),(product_label(rows[0]),slug)])]}
    graph = [crumbs]
    if live:
        product = {'@type':'Product','@id':BASE+slug+'#product','name':product_label(rows[0])+' · '+str(rows[0]['weight_kg'])+' kg','brand':{'@type':'Brand','name':rows[0]['brand']},'gtin'+str(len(key[0])):key[0], 'weight':{'@type':'QuantitativeValue','value':rows[0]['weight_kg'],'unitCode':'KGM'}}
        if str(rows[0].get('image','')).startswith('https://'):
            product['image'] = rows[0]['image']
        product['offers'] = {'@type':'AggregateOffer','priceCurrency':'EUR','lowPrice':min(o['price'] for o in live),'highPrice':max(o['price'] for o in live),'offerCount':len(live),'offers':[{'@type':'Offer','price':o['price'],'priceCurrency':'EUR','availability':'https://schema.org/InStock','url':merchant_url(o),'seller':{'@type':'Organization','name':o['merchant']}} for o in live]}
        graph.append(product)
    # Never invent ratings, priceValidUntil or observed-history dates.
    return {'@context':'https://schema.org','@graph':graph}


def render(template,key,rows,slug):
    rows = sorted(rows,key=lambda o:(not o['available'],o['price'],o['merchant']))
    seed = rows[0]
    title = product_label(seed)+' · '+str(seed['weight_kg'])+' kg: prezzi a confronto'
    cards = []
    for o in rows:
        action = ''
        if o['available']:
            rel = 'sponsored noopener noreferrer' if o.get('affiliate_url') else 'noopener noreferrer'
            action = f'<a class="btn secondary" href="{h(merchant_url(o),quote=True)}" target="_blank" rel="{rel}">Vai al negozio ↗</a>'
        daily = h(json.dumps({k:o.get(k) for k in ('price','weight_kg','available','checked_at','category')},separators=(',',':')),quote=True)
        disclosure = '<p class="micro">Possiamo ricevere una commissione, senza costi aggiuntivi per te.</p>' if o.get('affiliate_url') else ''
        cards.append(f'<article class="panel"><h2>{h(o["merchant"])}</h2><p><a class="product-title-link" href="{h(merchant_url(o),quote=True)}" rel="{'sponsored noopener noreferrer' if o.get('affiliate_url') else 'noopener noreferrer'}">{h(o["title"])}</a></p><p>{h(o.get("variant") or "Formato dichiarato nel catalogo")} · {o["weight_kg"]} kg</p><p class="catalog-price"><strong>{o["price"]:.2f} €</strong></p><p>{o["price"]/o["weight_kg"]:.2f} €/kg · spedizione esclusa</p><p>{"Disponibile" if o["available"] else "Non disponibile"} al rilevamento</p><p class="micro">Recupero dati: <time datetime="{h(o["checked_at"],quote=True)}">{h(o["checked_at"])}</time></p>{action}{disclosure}<div data-history-offer="{h(o["id"],quote=True)}"></div><div data-daily-offer="{daily}"><p class="micro">Calcolo giornaliero disponibile con JavaScript e razione manuale.</p></div>{error_link(o)}</article>')
    query = urlencode(dict(gtin=key[0],weight=key[1],matchbrand=key[2]))
    reviewed=any(o.get('identity_review') for o in rows)
    identity_note='Abbinamento revisionato delle schede prodotto e della confezione; il GTIN proviene dalla scheda di riferimento e non è dichiarato da tutti i negozi.' if reviewed else 'Confronto basato sullo stesso codice GTIN, marca e peso netto dichiarati dai negozi.'
    body = f'<section class="pagehero"><div class="wrap"><nav aria-label="Percorso"><a href="index.html">Home</a> / <a href="confronti-prodotti.html">Confronti per prodotto</a></nav><h1>{h(title)}</h1><p>GTIN {h(key[0])} · marca {h(seed["brand"])} · peso netto {seed["weight_kg"]} kg.</p></div></section><section class="section"><div class="wrap"><p class="notice">{identity_note} Controlla comunque ricetta, etichetta e confezione. Prezzi rilevati, non in tempo reale; spedizione esclusa. Un prezzo inferiore non è automaticamente il totale più conveniente.</p><div class="catalog-grid">'+''.join(cards)+f'</div><h2>Confronta anche la spedizione</h2><p>Il comparatore permette di impostare quantità e destinazione. Il totale viene stimato soltanto se le condizioni del negozio e il peso di spedizione sono verificabili.</p><a class="btn" href="confronta-cibo.html?{h(query,quote=True)}">Apri il confronto completo →</a><p><a href="prodotti.html">Altri prodotti</a> · <a href="chi-siamo.html">Metodo e fonti</a> · <a href="confronta-cibo.html#manual-tool">Calcola il costo giornaliero con la razione del produttore</a></p><p class="micro">I cataloghi sono recuperati periodicamente; il feed del fornitore può avere un aggiornamento differito. Il prezzo valido è quello mostrato nel negozio prima del pagamento.</p></div></section>'
    output = page(template,slug,title,product_label(seed)+'. GTIN '+key[0]+': prezzi e costo al kg tra negozi, spedizione esclusa, con data di rilevamento.',body)
    schema = json.dumps(structured_data(key,rows,slug),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    output = output.replace('</body>','<script src="assets/daily-cost.js" defer></script><script src="assets/price-history.js" defer></script></body>')
    return output.replace('</head>','<script type="application/ld+json">'+schema+'</script></head>')


def build():
    catalog = json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    template = (ROOT/'site/chi-siamo.html').read_text()
    matched = groups(catalog['offers'])
    current, links, list_items = set(), [], []
    for key, rows in sorted(matched.items()):
        slug = slug_for(key)
        current.add(slug)
        (ROOT/f'site/{slug}.html').write_text(render(template,key,rows,slug))
        list_items.append((product_label(rows[0]),BASE+slug))
        links.append(f'<li><a href="{slug}.html">{h(product_label(rows[0]))} · {rows[0]["weight_kg"]} kg</a> · {len({o["merchant_id"] for o in rows})} negozi · GTIN {h(key[0])}</li>')
    for old in (ROOT/'site').glob('prezzi-*-*.html'):
        if re.fullmatch(r'prezzi-\d{8,14}-[0-9a-f]{10}',old.stem) and old.stem not in current:
            body = '<section class="pagehero"><div class="wrap"><h1>Confronto da aggiornare</h1><p>Non ci sono più dati recenti sufficienti per questo confronto. Non mostriamo i vecchi prezzi come attuali.</p><a href="confronti-prodotti.html">Confronti disponibili →</a></div></section>'
            old.write_text(page(template,old.stem,'Confronto da aggiornare','Prezzi e disponibilità non confermati.',body).replace('content="index,follow"','content="noindex,follow"'))
    body = '<section class="pagehero"><div class="wrap"><nav aria-label="Percorso"><a href="index.html">Home</a></nav><h1>Lo stesso prodotto, in più negozi</h1><p>Confronti con codice GTIN, marca e peso netto coincidenti. Ricette o formati diversi restano separati.</p></div></section><section class="section"><div class="wrap content"><p>La selezione dipende dai codici e dai pesi disponibili nei cataloghi, non dalle commissioni. Prezzi non in tempo reale; verifica sempre la confezione e la spedizione nel negozio.</p><ul>'+''.join(links)+'</ul><a href="confronta-cibo.html?matched=1">Filtra nel comparatore →</a></div></section>'
    (ROOT/'site/confronti-prodotti.html').write_text(append_list_schema(page(template,'confronti-prodotti','Confronti per GTIN: lo stesso prodotto in più negozi','Prodotti con stesso GTIN, marca e peso netto presenti in più negozi, con prezzi e date.',body),'Confronti per GTIN e formato',list_items))
    xml = (ROOT/'site/sitemap.xml').read_text()
    xml = re.sub(r'<url><loc>https://offerte4zampe.it/(?:prezzi-\d{8,14}-[0-9a-f]{10}|confronti-prodotti)</loc>.*?</url>','',xml,flags=re.S)
    for slug in sorted(current|{'confronti-prodotti'}):
        xml = xml.replace('</urlset>',f'<url><loc>{BASE+slug}</loc></url>\n</urlset>')
    (ROOT/'site/sitemap.xml').write_text(xml)
    home = ROOT/'site/index.html'
    home.write_text(home.read_text().replace('href="confronta-cibo.html?matched=1">Stesso prodotto', 'href="confronti-prodotti.html">Stesso prodotto'))
    print('Generated',len(matched),'exact-format comparisons')


if __name__ == '__main__':
    build()
