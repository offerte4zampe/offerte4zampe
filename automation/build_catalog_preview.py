"""Prerender the first 24 canonical product groups without browser catalog downloads."""
import gzip
import re
import json
from html import escape as h
from pathlib import Path
try:
    from automation.build_home_data import build, pick, replace_region
except ImportError:
    from build_home_data import build, pick, replace_region

ROOT = Path(__file__).resolve().parents[1]


def render_preview(html, catalog, now=None):
    import datetime as dt
    try:
        from .product_link import product_url
        from .freshness import label
        from .merchant_promotions import render as render_promotion
    except ImportError:
        from product_link import product_url
        from freshness import label
        from merchant_promotions import render as render_promotion
    now=now or dt.datetime.now(dt.timezone.utc)
    groups={}
    for o in catalog['offers']:
        try:
            fresh=0 <= (now-dt.datetime.fromisoformat(o['checked_at'].replace('Z','+00:00'))).total_seconds() <= 36*3600
        except (KeyError,ValueError,TypeError):fresh=False
        if not fresh or not o.get('available') or not isinstance(o.get('price'),(int,float)) or o['price']<=0:continue
        groups.setdefault(o.get('product_id') or o['id'],[]).append(o)
    ranked=sorted(groups.values(),key=lambda rows:(-len({o['merchant_id'] for o in rows}),str(rows[0].get('canonical_title') or rows[0]['title']).casefold(),rows[0]['id']))[:24]
    cards=[]
    for rows in ranked:
        o=min(rows,key=lambda r:(r['price'],r['id']));shops=len({r['merchant_id'] for r in rows})
        price=f"{o['price']:.2f}".replace('.',',')
        unit=(f" · {o['unit_price']:.2f} €/{o['unit_price_unit']}".replace('.',',') if o.get('unit_price') else f" · {o['price']/o['weight_kg']:.2f} €/kg".replace('.',',') if o.get('weight_kg') else '')
        image=o.get('image_local') or o.get('image','')
        img=f'<img src="{h(image,quote=True)}" alt="" width="150" height="130" loading="lazy">' if image.startswith('https://') or re.fullmatch(r'/img/p/[a-f0-9]{24}-400\.webp',image) else ''
        warning = '<p class="notice">'+h(label(o['checked_at'],now))+'</p>' if label(o['checked_at'],now) else ''
        cards.append(f'<article class="catalog-card">{img}<p class="micro">{shops} {"negozio" if shops==1 else "negozi"} · {h(o.get("brand",""))}</p><h3><a class="product-title-link" href="{h(product_url(o),quote=True)}">{h(o.get("canonical_title") or o["title"])}</a></h3><p>{h(o.get("canonical_format") or o.get("variant") or "Formato da verificare")}</p><p><strong>Da {price} €</strong>{unit} · spedizione esclusa</p><p class="micro">Rilevato: {h(o["checked_at"])} · {h(o["merchant"])} · disponibile al rilevamento</p>{render_promotion(o,now)}{warning}</article>')
    content='<h2>Prodotti e prezzi dal catalogo</h2><p>Primi '+str(len(cards))+' prodotti: precedenza ai confronti con più negozi, poi nome.</p>'
    content+='<div class="catalog-grid">'+''.join(cards)+'</div>' if cards else '<p>Nessuna selezione recente disponibile. <a href="/prodotti">Esplora le pagine prodotto</a>.</p>'
    html = replace_region(html, 'catalog-preview', content)
    return html


def main():
    catalog = json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    path = ROOT/'site/confronta-cibo.html'
    path.write_text(render_preview(path.read_text(), catalog))


if __name__ == '__main__':
    main()
