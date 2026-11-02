#!/usr/bin/env python3
"""Guarded Brevo campaign sender. Input must be independently validated editorial JSON."""
import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from automation.weekly_offer_validation import validate_payload

API = "https://api.brevo.com/v3"

def request(method, path, payload=None):
    key = os.environ["BREVO_API_KEY"]
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
        headers={"api-key": key, "accept": "application/json", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}

def main():
    path = Path(os.environ.get("NEWSLETTER_PAYLOAD", "newsletter-approved.json"))
    if not path.is_file():
        print("SKIP: validated newsletter payload missing; no email sent.")
        return
    p = json.loads(path.read_text(encoding="utf-8"))
    today = dt.datetime.now(dt.timezone.utc).date()
    if p.get("verified_on") != today.isoformat():
        raise ValueError("Offer verification must be dated today (UTC)")
    offers = validate_payload(p)
    for offer in offers:
        if not all(offer.get(k) for k in ("name", "price", "shop", "url", "format")):
            raise ValueError("Incomplete offer")
        if not offer["url"].startswith("https://"):
            raise ValueError("Offer URL must be HTTPS")
    subject = p.get("subject", "").strip()
    if not subject or len(subject) > 150:
        raise ValueError("Invalid subject")
    list_id = int(os.environ["BREVO_LIST_ID"])
    if list_id <= 0:
        raise ValueError("Invalid Brevo list ID")
    sender = os.environ.get("BREVO_SENDER", "capobranco@offerte4zampe.it")
    if sender.lower() != "capobranco@offerte4zampe.it":
        raise ValueError("Unexpected sender")
    rows = "".join(
        "<li><strong>" + html.escape(o["name"]) + "</strong> (" + html.escape(o["format"]) + ")"
        + " — " + html.escape(str(o["price"])) + " · " + html.escape(o["shop"])
        + ' · <a href="' + html.escape(o["url"], quote=True) + '">Vedi offerta</a></li>'
        for o in offers
    )
    body = ("<html><body><h1>Offerte da fiutare</h1><p>Prezzi rilevati dal catalogo il "
            + today.isoformat() + "; spedizione esclusa salvo diversa indicazione.</p><ul>"
            + rows + "</ul><p>Alcuni link possono essere affiliati: potremmo ricevere una commissione senza costi aggiuntivi.</p>"
            + "<p>Ricevi questa email perché hai confermato l'iscrizione. "
            + "Per disiscriverti usa il link nel piè di pagina.</p>"
            + '<p><a href="{{ unsubscribe }}">Disiscriviti</a></p></body></html>')
    if os.environ.get("BREVO_SEND_ENABLED") != "true":
        print("DRY RUN: content validated; sending disabled.")
        return
    campaign_name = "O4Z-auto-" + today.isoformat()
    # Prevent duplicate sends on rerun, including campaigns already created.
    existing = request("GET", "/emailCampaigns?limit=100&offset=0").get("campaigns", [])
    if any(c.get("name") == campaign_name for c in existing):
        print("SKIP: campaign already exists", campaign_name)
        return
    created = request("POST", "/emailCampaigns", {
        "name": campaign_name, "subject": subject,
        "sender": {"name": "Offerte a 4 Zampe", "email": sender},
        "recipients": {"listIds": [list_id]},
        "htmlContent": body,
        "replyTo": sender
    })
    cid = created["id"]
    print("Campaign created", cid)
    request("POST", f"/emailCampaigns/{cid}/sendNow", {})
    print("Campaign send requested", cid)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, urllib.error.HTTPError) as exc:
        print("FAIL CLOSED:", str(exc), file=sys.stderr)
        sys.exit(1)
