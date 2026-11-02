"""Publish crawlable discovery links using only existing canonical HTML pages."""
import json
import re
from collections import deque
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

try:
    from .build_sitemaps import Metadata
    from .build_brand_pages import BRANDS
except ImportError:
    from build_sitemaps import Metadata
    from build_brand_pages import BRANDS

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://offerte4zampe.it/'
GUIDES = [
    ('prezzo-confezione-o-prezzo-kg', 'Confezione o prezzo al kg?', 'Confronta taglie e multipack senza confondere il prezzo del sacco con il costo per kg.'),
    ('spedizione-gratuita-conviene', 'La spedizione gratuita conviene?', 'Valuta il totale del carrello e le condizioni del negozio prima di aggiungere prodotti.'),
    ('stesso-prodotto-formato-gtin', 'Stesso prodotto, formato e GTIN', 'Controlla ricetta, quantità e codice prima di mettere due prezzi a confronto.'),
    ('confrontare-prezzi-lettiere', 'Come confrontare le lettiere', 'Litri e kg non sono intercambiabili: leggi formato e unità di misura.'),
    ('leggere-storico-prezzi', 'Come leggere lo storico prezzi', 'Distingui le rilevazioni osservate dai prezzi mancanti e dagli sconti dichiarati.'),
    ('costo-crocchette-cane', 'Quanto costano le crocchette?', 'Usa la razione del produttore per stimare durata e costo giornaliero.'),
]


def inventory(site):
    pages = {}
    for path in sorted(site.glob('*.html')):
        meta = Metadata(path.read_text())
        try:
            url = urlsplit(meta.canonical or '')
            if url.scheme != 'https' or url.netloc != 'offerte4zampe.it' or url.query or url.fragment:
                continue
        except ValueError:
            continue
        pages['/' + path.name] = {'canonical': url.path, 'indexable': not any(x in meta.robots for x in ('noindex', 'none'))}
    return pages


def destination(href, pages):
    """Keep query and fragment intact; never infer a destination from a slug."""
    try:
        url = urlsplit(urljoin(BASE, unescape(href)))
    except ValueError:
        return href
    if url.scheme != 'https' or url.netloc != 'offerte4zampe.it':
        return href
    # Both product endpoints intentionally run the Worker and are tested separately.
    if url.path in ('/prodotto', '/prodotto.html'):
        return href
    page = pages.get(url.path)
    if not page:
        return href
    return urlunsplit(('', '', page['canonical'], url.query, url.fragment))


def normalize_links(html, pages):
    def anchor(match):
        text = match[0]
        if re.search(r'\bdownload(?:\s|=|>)', text):
            return text
        def href(m):
            value = destination(m[2], pages)
            return m[0] if value == m[2] else 'href=' + m[1] + escape(value, quote=True) + m[1]
        return re.sub(r'\bhref=([\"\'])(.*?)\1', href, text, flags=re.S)
    return re.sub(r'<a\b[^>]*>', anchor, html, flags=re.S)


def enrich(html, pages, home=False):
    active = {p['canonical'] for p in pages.values() if p['indexable']}
    if '/guide-risparmio' in active:
        def menu(m):
            return re.sub(r'(<a\b[^>]*href=\")[^\"]*(\"[^>]*>Guide</a>)', r'\1/guide-risparmio\2', m[0])
        html = re.sub(r'<nav\b(?=[^>]*\bid="navlinks")[^>]*>.*?</nav>', menu, html, flags=re.S)
    def footer(m):
        value = m[0]
        entries = [('guides', '/guide-risparmio', 'Guide pratiche'), ('brands', '/marche', 'Marche'), ('comparisons', '/confronti-prodotti', 'Confronti per prodotto')]
        links = ''.join(f'<li id="footer-{key}"><a href="{url}">{label}</a></li>' for key, url, label in entries if url in active and f'id="footer-{key}"' not in value)
        return value.replace('</ul>', links + '</ul>', 1)
    html = re.sub(r'<footer\b[^>]*>.*?</footer>', footer, html, flags=re.S)
    if home:
        # Commercial discovery hub: stable links to indexable landing pages.
        promoted = [
            ('/confronta-cibo', 'Confronta i prezzi', 'Prezzi rilevati nei negozi e costo unitario per scegliere lo stesso prodotto.'),
            ('/confronti-prodotti', 'Confronti multinegozio', 'Schede con prodotti e formati confrontabili tra diversi negozi.'),
            ('/marche', 'Offerte per marca', 'Trova prodotti e offerte delle marche disponibili nel catalogo.'),
            ('/black-friday-animali', 'Black Friday animali', 'Come riconoscere gli sconti reali e confrontare prezzi, costo al kg e spedizione.'),
        ]
        promo_cards = ''.join('<article class="feature"><h3><a href="' + escape(url) + '">' + escape(label) + '</a></h3><p>' + escape(desc) + '</p></article>' for url, label, desc in promoted if url in active)
        if promo_cards:
            promo = '<section id="home-shopping-paths" class="section"><div class="wrap"><h2 class="section-title">Trova offerte e confronti utili</h2><p>Parti dai prezzi rilevati e verifica il formato prima di acquistare.</p><div class="feature-grid">' + promo_cards + '</div></div></section>'
            if 'id="home-shopping-paths"' in html:
                html = re.sub(r'<section id="home-shopping-paths".*?</section>', lambda _: promo, html, count=1, flags=re.S)
            else:
                html = html.replace('</main>', promo + '</main>', 1)
        cards = ''.join(f'<article class="feature"><h3><a href="/{slug}">{label}</a></h3><p>{text}</p></article>' for slug, label, text in GUIDES if '/' + slug in active)
        if cards:
            section = '<section id="home-guides" class="section alt"><div class="wrap"><span class="kicker">Prima del prossimo acquisto</span><h2 class="section-title">Guide per confrontare meglio.</h2><p>Controlli pratici ed esempi del catalogo per valutare confezioni, spedizione e prezzi.</p><div class="feature-grid">' + cards + '</div><p><a href="/guide-risparmio">Tutte le guide al risparmio →</a> · <a href="/osservatorio-prezzi">Osservatorio dei prezzi rilevati →</a></p></div></section>'
            if 'id="home-guides"' in html:
                html = re.sub(r'<section id="home-guides".*?</section>', lambda _: section, html, flags=re.S)
            else:
                html = re.sub(r'<section\b[^>]*><div class="wrap"><div class="section-heading"><div><span class="kicker">Acquisti più consapevoli</span>.*?</section>', lambda _: section, html, flags=re.S)
        brands = {name: '/marca-' + slug for slug, name in BRANDS if '/marca-' + slug in active}
        try:
            brands.update({name:url for name,url in json.loads((ROOT/'site/data/brand-pages.json').read_text()).items() if url in active})
        except (OSError,ValueError):pass
        # Promote only precise brand destinations which exist and are indexable.
        def popular_region(m):
            value = m[0]
            for label, name in [('Royal Canin', 'Royal Canin'), ('Purina', 'Purina Pro Plan'), ('Trainer', 'Natural Trainer')]:
                if name in brands:
                    value = re.sub(r'<a\b[^>]*>' + re.escape(label) + r'</a>', lambda _: '<a href="' + brands[name] + '">' + name + '</a>', value)
            return value
        html = re.sub(r'<div class="popular-searches">.*?</div>', popular_region, html, flags=re.S)
        def brand_region(m):
            value = re.sub(r' data-brand-pages="[^"]*"', '', m[0])
            value = value.replace('id="home-brands"', 'id="home-brands" data-brand-pages="' + escape(json.dumps(brands, ensure_ascii=False), quote=True) + '"')
            def brand_link(a):
                label = unescape(re.sub('<[^>]*>', '', a[2])).strip()
                return '<a href="' + brands[label] + '">' + a[2] + '</a>' if label in brands else a[0]
            return re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', brand_link, value)
        html = re.sub(r'<div\b[^>]*\bid="home-brands"[^>]*>.*?</div>', brand_region, html, flags=re.S)
    return normalize_links(html, pages)


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.urls = []; self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.urls.append(urljoin(BASE, href))


def graph(site, pages):
    active = {p['canonical'] for p in pages.values() if p['indexable']}
    edges = {}
    for filename, meta in pages.items():
        if meta['indexable']:
            edges[meta['canonical']] = {urlsplit(destination(u, pages)).path for u in Links((site / filename[1:]).read_text()).urls if urlsplit(u).netloc == 'offerte4zampe.it' and urlsplit(destination(u, pages)).path in active}
    distances = {'/': 0}; queue = deque(['/'])
    while queue:
        source = queue.popleft()
        for target in edges.get(source, set()):
            if target not in distances:
                distances[target] = distances[source] + 1; queue.append(target)
    return {'indexable_pages': len(active), 'reachable_from_home': len(active & distances.keys()), 'unreachable': sorted(active - distances.keys()), 'max_link_depth': max(distances.values(), default=0)}


def build(site=None):
    site = Path(site or ROOT / 'site'); pages = inventory(site)
    before = graph(site, pages); changed = 0
    for path in sorted(site.glob('*.html')):
        old = path.read_text(); new = enrich(old, pages, home=path.name == 'index.html')
        if old != new:
            path.write_text(new); changed += 1
    after = graph(site, pages)
    report = {'method_version': 1, 'before': before, 'after': after}
    (site / 'data').mkdir(exist_ok=True)
    (site / 'data/discovery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Discovery pages updated:', changed, 'Graph:', after)


if __name__ == '__main__':
    build()
