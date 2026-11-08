"""Generate crawlable category pages from the same merchant catalog used by the UI."""
import gzip, json, re
from pathlib import Path
from html import escape as h
from urllib.parse import quote

try:
    from automation.list_schema import append_list_schema
except ImportError:
    from list_schema import append_list_schema


try:
    from automation.report_link import error_link
except ImportError:
    from report_link import error_link

try:
    from .product_link import product_url
except ImportError:
    from product_link import product_url

# Search-specific navigation uses the existing comparator; no thin landing pages.
SEARCH_INTENTS = {
    'lettiere-gatti': [
        ('Lettiera in silicio', 'lettiera silicio', 'Controlla il volume dichiarato: litri e kg non sono intercambiabili.'),
        ('Lettiera vegetale e tofu', 'lettiera tofu', 'Verifica materiale, formato e indicazioni del produttore.'),
        ('Lettiera agglomerante', 'lettiera agglomerante', 'Confronta confezioni comparabili e aggiungi la spedizione.'),
    ],
    'crocchette-cani': [
        ('Crocchette 20 kg', 'crocchette 20 kg', 'Controlla ricetta, conservazione e prezzo al kg.'),
        ('Crocchette 12 kg', 'crocchette 12 kg', 'Confronta soltanto la stessa ricetta e la stessa linea.'),
        ('Monge e Royal Canin', 'Monge Royal Canin', 'Cerca la linea e il formato esatti: le ricette non sono equivalenti.'),
    ],
    'crocchette-gatti': [
        ('Crocchette sterilized', 'crocchette gatto sterilized', 'Verifica linea e fascia di età sulla confezione.'),
        ('Crocchette kitten', 'crocchette kitten', 'Le ricette kitten non sono intercambiabili con quelle adult.'),
        ('Royal Canin e Purina', 'Royal Canin Purina', 'Seleziona marca, formato e ricetta esatti.'),
    ],
}


def intent_html(slug):
    rows = SEARCH_INTENTS.get(slug, [])
    if not rows:
        return ''
    links = ''.join(
        '<li><a href="/confronta-cibo?q=' + quote(query) + '">' + h(label) +
        '</a> — ' + h(description) + '</li>'
        for label, query, description in rows
    )
    return '<section aria-labelledby="ricerche-frequenti"><h2 id="ricerche-frequenti">Ricerche utili per confrontare i prodotti</h2><p>Esplora il catalogo per materiale, formato o linea. I risultati non sono classifiche dei prodotti più venduti.</p><ul>' + links + '</ul></section>'


def category_items(selected):
    """Structured lists link to canonical product pages, not affiliate destinations."""
    return [
        (o['title'] + ' — ' + (o.get('variant') or ''), 'https://offerte4zampe.it' + product_url(o))
        for o in selected if product_url(o).startswith('/prodotto/')
    ]

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [
 ('crocchette-cani', 'Crocchette per cani: prezzi e offerte', 'crocchette cani', ('cani > cibo > secco', 'crocchette cani'), 'Confronta lo stesso alimento, la stessa ricetta e lo stesso formato. Un sacco più economico può contenere meno prodotto: quando il peso è dichiarato, controlla anche il prezzo al chilo. Le diete veterinarie presenti nel catalogo non sono consigli alimentari: segui le indicazioni del veterinario.'),
 ('crocchette-gatti', 'Crocchette per gatti: prezzi e offerte', 'crocchette gatti', ('gatti > cibo > secco', 'crocchette gatti'), 'Prima di confrontare il prezzo, controlla ricetta, fascia di età e quantità della confezione. Adult, kitten e alimenti veterinari non sono prodotti intercambiabili. Il prezzo al chilo aiuta a confrontare formati dello stesso alimento, ma non descrive il costo giornaliero senza conoscere la razione.'),
 ('lettiere-gatti', 'Lettiere per gatti: prezzi e offerte', 'lettiera', ('lettier',), 'Confronta tipo di materiale, volume o peso e numero di confezioni. Litri e chilogrammi non sono equivalenti: non convertiamo automaticamente le unità. Prima di comprare verifica anche il costo di spedizione, che può incidere sul prezzo finale delle confezioni pesanti.')]

def matches(offer, needles):
    category = offer.get('category', '').casefold()
    return any(n in category for n in needles)

def build():
    catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    template=(ROOT/'site/chi-siamo.html').read_text()
    date=catalog['generated_at'][:10]
    for slug,title,query,needles,guide in CATEGORIES:
        candidates=[o for o in catalog['offers'] if o.get('available') and o.get('price',0)>0 and o.get('url','').startswith('https://') and matches(o,needles)]
        candidates.sort(key=lambda o:(o['title'].casefold(), o.get('variant',''), o['merchant']))
        # Rotate sources for a readable selection, not a ranking of incomparable packages.
        groups={m:[o for o in candidates if o['merchant']==m] for m in sorted({o['merchant'] for o in candidates})}
        selected=[]
        while len(selected)<24 and any(groups.values()):
            for group in groups.values():
                if group and len(selected)<24: selected.append(group.pop(0))
        cards=[]
        for o in selected:
            price=f"{o['price']:.2f}".replace('.',',')
            unit=f" · {o['price']/o['weight_kg']:.2f} €/kg".replace('.',',') if o.get('weight_kg') else ''
            cards.append(f'<article class="panel"><p class="micro">{h(o["merchant"])} · {h(o.get("brand", ""))}</p><h2 style="font-size:1.1rem"><a class="product-title-link" href="{h(product_url(o),quote=True)}">{h(o["title"])}</a></h2><p>{h(o.get("variant", ""))}</p><p><strong>{price} €</strong>{unit}</p><p class="micro">Rilevato il {h(o["checked_at"][:10])} · spedizione esclusa</p><a class="btn" href="confronta-cibo.html?q={quote(o["title"])}">Confronta le offerte →</a> <a href="{h(o.get("affiliate_url") or o["url"],quote=True)}" rel="sponsored noopener noreferrer" target="_blank">Vedi nel negozio ↗</a>{error_link(o)}</article>')
        links=' · '.join(f'<a href="{s}.html">{h(t)}</a>' for s,t,*_ in CATEGORIES if s!=slug)
        body=f'<main id="main"><section class="pagehero"><div class="wrap"><span class="eyebrow">Cataloghi reali · aggiornamento automatico</span><h1>{h(title)}</h1><p>{h(guide)}</p><a class="btn" href="confronta-cibo.html?q={quote(query)}">Cerca nel comparatore →</a></div></section><section class="section"><div class="wrap"><p>Catalogo aggiornato il {date}. {len(candidates)} offerte disponibili in questa categoria tra i negozi importati. Qui mostriamo fino a 24 offerte, alternate per negozio e ordinate per nome: non è una classifica di convenienza.</p><p class="notice">Prezzi e disponibilità possono cambiare. Verifica ricetta, formato, spedizione e prezzo finale nel negozio. Non confrontiamo tutto il mercato. I link Bauzaar e Isola dei Tesori sono commerciali: possiamo ricevere una commissione, senza costi aggiuntivi per te.</p><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:20px">{"".join(cards) or "<p>Nessuna offerta disponibile in questa rilevazione. Usa il comparatore per controllare il catalogo.</p>"}</div>{intent_html(slug)}<h2>Altre categorie</h2><p>{links}</p><h2>Come leggiamo i prezzi</h2><p>Usiamo feed ufficiali e cataloghi pubblici dei negozi. Non presumiamo che due nomi simili indichino lo stesso prodotto e non inventiamo pesi mancanti. La selezione viene rigenerata insieme al catalogo ogni sei ore. <a href="chi-siamo.html">Leggi il metodo</a>.</p></div></section></main>'
        page=re.sub(r'<main\b.*?</main>',lambda _:body,template,flags=re.S)
        page=re.sub(r'<title>.*?</title>',f'<title>{h(title)} | Offerte a 4 Zampe</title>',page)
        page=re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*',lambda m:m[1]+h(guide,quote=True),page)
        page=re.sub(r'(<meta property="og:title" content=")[^"]*',lambda m:m[1]+h(title+' | Offerte a 4 Zampe',quote=True),page)
        page=page.replace('https://offerte4zampe.it/chi-siamo',f'https://offerte4zampe.it/{slug}')
        page=page.replace(' aria-current="page"','')
        page=append_list_schema(page,title,category_items(selected))
        (ROOT/f'site/{slug}.html').write_text(page)
    sitemap=ROOT/'site/sitemap.xml'; text=sitemap.read_text()
    for slug,*_ in CATEGORIES:
        text=re.sub(r'<url><loc>https://offerte4zampe.it/'+slug+r'</loc>.*?</url>','',text,flags=re.S)
        text=text.replace('</urlset>',f'<url><loc>https://offerte4zampe.it/{slug}</loc><lastmod>{date}</lastmod></url>\n</urlset>')
    sitemap.write_text(text)
    print('Generated 3 category pages from',len(catalog['offers']),'offers')
if __name__=='__main__': build()
