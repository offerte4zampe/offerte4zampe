"""Render only dated, cart-tested coupons; no partner-provided bypass. Never renew evidence during a build."""
import datetime as dt
import json
import re
from html import escape as h
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'bauzaar': 'www.bauzaar.it', 'isola': 'www.isoladeitesori.it', 'paco': 'www.pacopetshop.it', 'hygge': 'hyggepetfood.com'}


def stamp(value):
    date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('Timezone required')
    return date


def eligible(row, now):
    try:
        proof = row['cart_test']
        verified = stamp(row['verified_at'])
        end = min(stamp(row['expires_at']), stamp(row['recheck_after']), verified + dt.timedelta(hours=48))
        return (row['status'] == 'cart_tested' and row['publication_allowed'] is True
                and stamp(row['starts_at']) <= now < end and verified <= now
                and re.fullmatch(r'[A-Z0-9_-]{2,40}', row['code']) is not None
                and proof['code'] == row['code'] and proof['currency'] == 'EUR'
                and type(proof['before_cents']) is int and type(proof['after_cents']) is int
                and 0 < proof['after_cents'] < proof['before_cents']
                and bool(proof['product']) and bool(proof['variant'])
                and all(urlsplit(row[k]).scheme == 'https' and urlsplit(row[k]).netloc == HOSTS[row['shop']]
                        for k in ['source_url', 'destination_url']))
    except (KeyError, ValueError, TypeError, AttributeError):
        return False



def render_card(row):
    p = row['cart_test']
    money = lambda n: f'{n/100:.2f}'.replace('.', ',') + ' €'
    until = min(stamp(row['expires_at']), stamp(row['recheck_after']), stamp(row['verified_at']) + dt.timedelta(hours=48)).isoformat()
    return f'''<article class="coupon" data-shop="{h(row['shop'])}" data-valid-until="{h(until)}">
<div class="shop"><span class="shop-logo"><img src="assets/shops/bauzaar.svg" alt="Logo Bauzaar" width="112" height="62"></span><div><strong>{h(row['merchant'])}</strong><small>Negozio partner</small></div></div>
<div class="discount">{h(row['benefit'])}</div><h2>{h(row['title'])}</h2><p class="description">{h(row['description'])}</p><span class="status">Provato nel carrello · {h(row['checked_date'])}</span>
<div class="card-tail"><div class="code-row"><code>{h(row['code'])}</code><button class="copy" data-code="{h(row['code'])}" aria-label="Copia il codice {h(row['code'])}">Copia codice</button></div>
<a class="shop-button coupon-visit" href="{h(row['destination_url'], quote=True)}" target="_blank" rel="noopener noreferrer">Vai alla selezione del negozio ↗</a>
<details><summary>Condizioni e prova effettuata</summary><p>{h(row['conditions'])}</p><p><strong>Prova su:</strong> {h(p['product'])}, {h(p['variant'])}. Prezzo della riga da {money(p['before_cents'])} a {money(p['after_cents'])}. {h(p.get('note', ''))}</p><p>Questa prova riguarda il prodotto indicato, non ogni possibile carrello. Prezzi e disponibilità possono cambiare. Spedizione esclusa.</p><p><a href="{h(row['source_url'], quote=True)}" target="_blank" rel="noopener noreferrer">Condizioni pubblicate dal negozio</a></p></details>
<p class="footnote">Scade il {h(row['expires_label'])}. Ultima prova: {h(row['checked_date'])}.</p></div></article>'''


def build(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    data = json.loads((ROOT/'automation/coupons.json').read_text())
    rows = [r for r in data['coupons'] if eligible(r, now)]
    cards = ''.join(render_card(r) for r in rows)
    shell = (ROOT/'automation/coupon-layout.html').read_text()
    body = shell.replace('<!-- COUPON_CARDS -->', cards)
    template = (ROOT/'site/chi-siamo.html').read_text()
    out = re.sub(r'<main\b.*?</main>', lambda _: '<main id="main" class="coupon-page">'+body+'</main>', template, flags=re.S)
    out = out.replace('https://offerte4zampe.it/chi-siamo', 'https://offerte4zampe.it/codici-sconto')
    out = re.sub(r'<title>.*?</title>', '<title>Codici sconto provati per animali | Offerte a 4 Zampe</title>', out)
    for key in ['name="description"', 'property="og:description"', 'property="og:title"']:
        out = re.sub('(<meta '+key+' content=")[^"]*', lambda m: m[1]+'Codici sconto per animali: condizioni, scadenze e prove nel carrello dei negozi.', out)
    out = out.replace(' aria-current="page"', '')
    out = out.replace('</head>', '<link rel="stylesheet" href="assets/coupons.css?v=1"></head>')
    out = out.replace('</body>', '<script src="assets/coupons.js?v=1" defer></script></body>')
    (ROOT/'site/codici-sconto.html').write_text(out)
    print('Cart-tested coupons published:', len(rows))


if __name__ == '__main__':
    build()
