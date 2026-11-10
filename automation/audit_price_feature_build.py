"""Audit only the post-build, unpublished Cloudflare static asset directory.

Accept generic uses like a shipping threshold and monitoring an insurance policy.
Disallow historical-price promises, personalized price targets and historical data.
Output machine-readable, bounded findings for review.
"""
import argparse
import gzip
import json
import re
from pathlib import Path

TERMS = re.compile(r"storico|minimo storico|massimo storico|avvis[oi]|alert|ribass\w*|monitor\w*|soglia|preferiti|buon momento|prezzo pi[uù] basso di sempre", re.I)
PRICE_BLOCK = re.compile(
    r"\bstoric\w*\b|\bpreferiti\b|\bbuon momento\b|\bprezzo pi[uù] basso di sempre\b|\bribassi? verificati\b"
    r"|\b(?:avvis[oi]|alert|soglia|monitor\w*|ribass\w*)\b.{0,55}\bprezz\w*\b"
    r"|\bprezz\w*\b.{0,55}\b(?:avvis[oi]|alert|soglia|monitor\w*|ribass\w*)\b",re.I)
DANGEROUS_HOOKS = re.compile(r"data-history-offer\s*=|data-watch-add\s*=|data-watch-save\s*=|class=['\"][^'\"]*observed-history|id=['\"]watch-items",re.I)
HISTORICAL_ASSETS = ['data/price-history.json.gz','data/price-observatory.json','data/history']
AMAZON_DISCLOSURE = 'In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei'

def audit(site):
    site=Path(site)
    findings=[]
    bad=[]
    pages=0
    for path in sorted(site.rglob('*.html')):
        relative=path.relative_to(site).as_posix()
        text=path.read_text(encoding='utf-8', errors='replace')
        pages+=1
        # Strip script content but retain JSON-LD, page text, attributes and meta.
        for match in TERMS.finditer(text):
            context=text[max(0,match.start()-75):min(len(text),match.end()+95)]
            # Generic form accessibility alerts and delivery thresholds are not price alerts.
            semantic='generic-context-review' if (
                (match.group(0).casefold()=='alert' and re.search(r'role=[\"\\\']alert[\"\\\']',context,re.I))
                or (match.group(0).casefold()=='soglia' and re.search(r'spedizione|spedire|consegna|articoli',context,re.I)
                    and not re.search(r'avvis[oi]|notific|prezzo desiderato|price.alert',context,re.I))
            ) else None
            label=semantic or ('disabled-price-feature' if PRICE_BLOCK.search(context) else 'generic-context-review')
            if label=='disabled-price-feature': bad.append((relative,match.group(0),context))
            findings.append({'path':relative,'term':match.group(0),'decision':'remove_or_rewrite' if label=='disabled-price-feature' else 'retain_contextual','context':re.sub(r'\s+',' ',context)[:170]})
        if DANGEROUS_HOOKS.search(text):
            bad.append((relative,'history_or_watchlist_dom','static HTML contains disabled feature control'))
        if re.search(r'<a\b[^>]*href=["\'][^"\']*(?:/preferiti|/osservatorio-prezzi|/leggere-storico-prezzi)',text,re.I):
            bad.append((relative,'disabled_navigation','internal disabled-feature link'))
        if relative=='prodotto.html':
            if AMAZON_DISCLOSURE not in text:
                bad.append((relative,'amazon_disclosure','Amazon disclosure missing from product page footer'))
    for item in HISTORICAL_ASSETS:
        p=site/item
        if p.is_file() or (p.is_dir() and any(p.rglob('*'))):
            bad.append((item,'historical_asset','historical data still in deploy assets'))
    for xml in site.glob('sitemap*.xml'):
        x=xml.read_text(encoding='utf-8')
        if re.search(r'/(?:preferiti|osservatorio-prezzi|leggere-storico-prezzi)(?:<|/)',x):
            bad.append((xml.name,'disabled_sitemap','disabled feature in sitemap'))
    # A compressed product snapshot must not carry previously observed historical records.
    snapshot=site/'data/product-catalog.json.gz'
    if snapshot.exists():
        try:
            catalog=json.loads(gzip.decompress(snapshot.read_bytes()))
            if re.search(r'"history"\s*:\s*\[\s*\{',json.dumps(catalog,separators=(',',':'))):
                bad.append(('data/product-catalog.json.gz','historical_series','embedded product history in distributable snapshot'))
        except (OSError,ValueError) as e:
            bad.append(('data/product-catalog.json.gz','invalid_snapshot',type(e).__name__))
    return {'pages_scanned':pages,'occurrences':findings[:2000],'occurrence_count':len(findings),
            'violations':[{'path':p,'term':t,'context':str(c)[:160]} for p,t,c in bad[:500]],
            'violation_count':len(bad)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',default='site')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    report=audit(args.site)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"Generated asset audit: {report['pages_scanned']} HTML, {report['occurrence_count']} contextual occurrences, {report['violation_count']} prohibited occurrences")
    for item in report['violations'][:25]:
        print('VIOLATION',item['path'],item['term'],item['context'])
    if report['violation_count']:
        raise SystemExit(1)
if __name__=='__main__':
    main()
