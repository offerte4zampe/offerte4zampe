"""Build canonical-only sitemap partitions and record observed content changes.

The initial inventory omits lastmod rather than inventing historical edit dates.
Refresh timestamps alone do not count as significant content changes.
"""
import datetime
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://offerte4zampe.it/'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', NS)


class Metadata(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonical = None
        self.robots = ''
        self.title = ''
        self.description = ''
        self.in_title = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots = attrs.get('content','').lower()
        if tag == 'meta' and attrs.get('name') == 'description':
            self.description = attrs.get('content','')
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def fingerprint(html):
    metadata = Metadata(html)
    main = re.search(r'<main\b[^>]*>(.*?)</main>',html,re.S)
    content = main[1] if main else ''
    content = re.sub(r'<time\b[^>]*>.*?</time>','<time></time>',content,flags=re.S)
    # Normalized feeds use ISO timestamps. Do not advance lastmod just for a fetch.
    content = re.sub(r'\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?','[date]',content)
    content = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}(?:,? \d{1,2}:\d{2}(?::\d{2})?)?','[date]',content)
    schema = re.findall(r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',html,re.S)
    value = json.dumps([metadata.title,metadata.description,content,schema],ensure_ascii=False)
    return hashlib.sha256(value.encode()).hexdigest()


def group_for(path, html):
    slug = path.stem
    if 'blog' in path.parts and path.name == 'index.html':
        return 'guides'
    if slug.startswith(('marca-','linea-')) or slug == 'marche':
        return 'brands'
    if slug in ['crocchette-cani','crocchette-gatti','lettiere-gatti']:
        return 'categories'
    if slug.startswith(('prezzi-','monge-','royal-canin-','pro-plan-')) or slug in ['prodotti','confronti-prodotti']:
        return 'products'
    if re.search(r'"@type"\s*:\s*"Article"',html):
        return 'guides'
    return 'pages'


def inventory(site, old, now):
    state, partitions = {}, defaultdict(list)
    # Editorial posts are nested HTML pages. Do not descend into generated product
    # directories: canonical product URLs are already imported from their manifest.
    pages = list(site.glob('*.html')) + list((site / 'blog').rglob('index.html'))
    for path in sorted(pages):
        html = path.read_text()
        meta = Metadata(html)
        if not meta.canonical or 'noindex' in meta.robots or 'none' in meta.robots:
            continue
        url = urlsplit(meta.canonical)
        if url.scheme != 'https' or url.netloc != 'offerte4zampe.it' or url.query or url.fragment:
            continue
        if meta.canonical in state:
            raise ValueError('Duplicate canonical: '+meta.canonical)
        current_hash = fingerprint(html)
        previous = old.get(meta.canonical)
        lastmod = previous.get('lastmod') if previous else None
        if previous and previous['content_hash'] != current_hash:
            lastmod = now
        entry = dict(content_hash=current_hash,lastmod=lastmod)
        state[meta.canonical] = entry
        partitions[group_for(path,html)].append((meta.canonical,lastmod))
    return state, partitions


def xml_write(path, root):
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def build():
    state_path = ROOT/'automation/sitemap-state.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    state, parts = inventory(ROOT/'site',previous,now)
    canonical_path=ROOT/'site/data/canonical-sitemap.json'
    if canonical_path.exists():
        for row in json.loads(canonical_path.read_text()):
            if not row['url'].startswith(BASE+'prodotto/'):raise ValueError('Unexpected canonical product URL')
            if row['url'] in state:raise ValueError('Duplicate canonical product')
            state[row['url']]={'content_hash':row['content_hash'],'lastmod':row.get('lastmod')}
            parts['products'].append((row['url'],row.get('lastmod')))
    if not state:
        raise ValueError('No canonical pages found; preserve prior sitemap')
    index = ET.Element('{'+NS+'}sitemapindex')
    active = set()
    for name, urls in sorted(parts.items()):
        filename = 'sitemap-'+name+'.xml'
        active.add(filename)
        root = ET.Element('{'+NS+'}urlset')
        for url, lastmod in urls:
            node = ET.SubElement(root,'{'+NS+'}url')
            ET.SubElement(node,'{'+NS+'}loc').text = url
            if lastmod:
                ET.SubElement(node,'{'+NS+'}lastmod').text = lastmod
        xml_write(ROOT/'site'/filename,root)
        ET.SubElement(ET.SubElement(index,'{'+NS+'}sitemap'),'{'+NS+'}loc').text = BASE+filename
    # Old partition files are never advertised by the current index.
    xml_write(ROOT/'site/sitemap.xml',index)
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print('Sitemap partitions:',{name:len(urls) for name,urls in parts.items()})


if __name__ == '__main__':
    build()
