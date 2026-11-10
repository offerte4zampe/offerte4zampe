#!/usr/bin/env python3
"""Build weekly site article and social copy from the exact newsletter payload."""
import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from automation.weekly_offer_validation import validate_payload
from automation.apply_navigation import apply as apply_navigation

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "newsletter-approved.json"
SITE = ROOT / "site"
def build():
    p = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    validate_payload(p)
    if p.get("verified_on") != day:
        raise ValueError("Newsletter selection missing, stale or incomplete")
    slug = "offerte-settimana-" + day
    path = SITE / "offerte" / (slug + ".html")
    path.parent.mkdir(parents=True, exist_ok=True)
    title = "5 prodotti per animali da confrontare" if len(p["offers"]) == 5 else "Prodotti per animali da confrontare"
    heading = f"{title} · {day}"
    items = []
    media = []
    social = [f"🐾 Offerte da fiutare · {day}", "Ecco i prodotti selezionati questa settimana dal nostro comparatore:"]
    for o in p["offers"]:
        url = str(o["url"])
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Unsafe offer link")
        name = str(o["name"])
        price = str(o["price"])
        shop = str(o["shop"])
        fmt = str(o["format"])
        photo = str(o["image"])
        media.append({"name": name, "format": fmt, "url": photo, "source": "catalog_feed_unverified_visually"})
        items.append(f'<li><img src="{html.escape(photo, quote=True)}" alt="{html.escape(name, quote=True)}" loading="lazy" width="180"><strong>{html.escape(name)}</strong> ({html.escape(fmt)}) — {html.escape(price)} da {html.escape(shop)}. <a rel="nofollow sponsored noopener" href="{html.escape(url, quote=True)}">Controlla prezzo e disponibilità</a></li>')
        social.append(f"• {name} ({fmt}) — {price} · {shop}")
    article_url = f"https://offerte4zampe.it/offerte/{slug}.html"
    social.extend(["", "Prezzi rilevati dal catalogo: verifica sempre il prezzo finale e la spedizione presso il negozio.", f"🔎 Dettagli: {article_url}", "Alcuni collegamenti possono essere affiliati. #Offerte4Zampe #AnimaliDomestici"])
    page = f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(heading)} | Offerte a 4 Zampe</title><meta name="description" content="Cinque prodotti per animali selezionati dal catalogo, con prezzi e negozi da confrontare."><link rel="canonical" href="{article_url}"><link rel="stylesheet" href="/assets/style.css"></head><body><header></header><main class="wrap content"><p><a href="/">Offerte a 4 Zampe</a></p><h1>{html.escape(heading)}</h1><p>Una selezione basata sul prezzo per unità di peso, non una classifica di sconti. Rilevazioni del {day}: prezzi e disponibilità possono variare; spedizione esclusa salvo indicazione diversa.</p><ol>{''.join(items)}</ol><p>Prima di acquistare, confronta il prezzo totale e controlla formato, disponibilità e condizioni del negozio.</p><p>Trasparenza: alcuni collegamenti sono affiliati e possiamo ricevere una commissione senza costi aggiuntivi per te.</p><p><a href="/">Torna al comparatore</a></p></main><footer></footer><script src="/assets/base.js" defer></script></body></html>"""
    path.write_text(apply_navigation(page), encoding="utf-8")
    out = ROOT / "automation" / "weekly-social-draft.json"
    out.write_text(json.dumps({"date":day,"article_url":article_url,"facebook": "\n".join(social), "instagram": "\n".join(social).replace(article_url,"Link all'articolo nel sito: offerte4zampe.it"),"media":media,"status":"draft_not_published_requires_visual_verification"},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Built", path.relative_to(ROOT), "and social draft")
if __name__ == "__main__":
    build()
