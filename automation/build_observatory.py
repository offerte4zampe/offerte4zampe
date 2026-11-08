"""Descriptive monthly matched-offer observations, not a market inflation index."""
import calendar
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from collections import defaultdict
from html import escape as h
from pathlib import Path
try:
    from .build_product_pages import page
except ImportError:
    from build_product_pages import page

try:
    from .price_merchant_policy import price_history_allowed
except ImportError:
    from price_merchant_policy import price_history_allowed
ROOT=Path(__file__).resolve().parents[1]
# Minimum coverage is editorial, never proof of a representative market sample.
MIN_DAYS=7
MIN_PAIRS=10
MIN_MERCHANTS=2


def fingerprint(offer):
    return hashlib.sha256(json.dumps([offer.get(k) for k in ('merchant_id','title','variant','brand','gtin','weight_kg')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def positive(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>0


def previous_month(month):
    return (dt.date.fromisoformat(month+'-01')-dt.timedelta(days=1)).isoformat()[:7]


def calculate(catalog,history,today):
    cutoff=today-dt.timedelta(days=179)
    categories=defaultdict(lambda:defaultdict(dict))
    seen=set()
    for o in catalog.get('offers',[]):
        oid=o.get('id')
        if not oid or oid in seen or not price_history_allowed(o.get('merchant_id')):continue
        seen.add(oid)
        category=o.get('category','').strip()
        if not category or not o.get('merchant_id') or not positive(o.get('weight_kg')):continue
        if history.get('identities',{}).get(oid)!=fingerprint(o):continue
        days={}
        duplicates=set()
        for row in history.get('offers',{}).get(oid,[]):
            try:
                day=dt.date.fromisoformat(row['day'])
                checked=dt.datetime.fromisoformat(row['checked_at'].replace('Z','+00:00'))
                if checked.tzinfo is None or checked.astimezone(dt.timezone.utc).date()!=day:continue
                if not cutoff<=day<=today or row.get('available') is not True:continue
                if not all(positive(row.get(k)) for k in ('low','last','high')):continue
                if not row['low']<=row['last']<=row['high']:continue
                # Ambiguous duplicates are discarded, never counted twice or averaged.
                if day in days:duplicates.add(day)
                days[day]=row['last']
            except (KeyError,ValueError,TypeError,AttributeError):continue
        months=defaultdict(list)
        for day,price in days.items():
            if day not in duplicates:months[day.isoformat()[:7]].append((day.isoformat(),price))
        for month,values in months.items():
            categories[category][month][oid]=dict(merchant_id=o['merchant_id'],days=len(values),first=min(v[0] for v in values),last=max(v[0] for v in values),mean=statistics.mean(v[1] for v in values))
    result=[]
    for category,months in sorted(categories.items()):
        for month,offers in sorted(months.items()):
            prev=previous_month(month)
            panel=[]
            for oid,current in sorted(offers.items()):
                base=months.get(prev,{}).get(oid)
                if base and base['days']>=MIN_DAYS and current['days']>=MIN_DAYS and positive(current['mean']/base['mean']):
                    panel.append(dict(offer_id=oid,merchant_id=current['merchant_id'],base_days=base['days'],current_days=current['days'],base_mean=base['mean'],current_mean=current['mean'],ratio=current['mean']/base['mean']))
            closed=month<today.isoformat()[:7]
            enough=len(panel)>=MIN_PAIRS and len({v['merchant_id'] for v in panel})>=MIN_MERCHANTS
            publish=closed and enough
            reason='available' if publish else ('month_open' if not closed else 'insufficient_matched_panel')
            # Equal-weight geometric mean of within-offer price relatives.
            index=100*math.exp(statistics.mean(math.log(v['ratio']) for v in panel)) if publish else None
            if index is not None and not positive(index):
                index=None
                reason='invalid_numeric_range'
                publish=False
            result.append(dict(category=category,month=month,previous_month=prev,closed=closed,offers=len(offers),merchants=len({v['merchant_id'] for v in offers.values()}),observed_days_min=min(v['days'] for v in offers.values()),observed_days_max=max(v['days'] for v in offers.values()),first=min(v['first'] for v in offers.values()),last=max(v['last'] for v in offers.values()),matched_offers=len(panel),matched_merchants=len({v['merchant_id'] for v in panel}),index_previous_month_100=index,status=reason,panel=panel if publish else []))
    return dict(method_version=1,generated_on=today.isoformat(),retention_days=180,minimum_days_per_offer_month=MIN_DAYS,minimum_matched_offers=MIN_PAIRS,minimum_matched_merchants=MIN_MERCHANTS,months=result)


def render(template,data):
    rows=[]
    for row in data['months']:
        value='Mese in corso: indice non pubblicato' if not row['closed'] else 'Campione comparabile insufficiente'
        if row['index_previous_month_100'] is not None:
            value=f'{row["index_previous_month_100"]:.2f}'.replace('.',',')+' (mese precedente = 100)'
        rows.append(f'<tr><td>{h(row["category"])}</td><td>{h(row["month"])}</td><td>{h(row["first"])} – {h(row["last"])}</td><td>{row["offers"]} / {row["merchants"]}</td><td>{row["observed_days_min"]} – {row["observed_days_max"]}</td><td>{row["matched_offers"]} / {row["matched_merchants"]}</td><td>{h(value)}</td></tr>')
    table='<p>Non ci sono ancora osservazioni con identità verificata. Nessun indice viene ricostruito.</p>'
    if rows:
        table='<div class="guide-table" tabindex="0" role="region" aria-label="Copertura mensile osservatorio"><table><caption>Offerte del catalogo seguito: prezzi della confezione, spedizione esclusa</caption><thead><tr><th>Categoria dichiarata</th><th>Mese UTC</th><th>Date effettive</th><th>Offerte / negozi</th><th>Giorni per offerta, min–max</th><th>Abbinate / negozi</th><th>Indice descrittivo</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    body='<section class="pagehero"><div class="wrap"><h1>Osservatorio prezzi per animali</h1><p>Copertura mensile delle rilevazioni di Offerte a 4 Zampe, senza ricostruire dati mancanti.</p><p class="micro">Redazione Offerte a 4 Zampe · calcolo del '+h(data['generated_on'])+' UTC · metodo versione 1.</p></div></section><section class="section"><div class="wrap content"><h2>Prima il campione, poi il numero</h2><p>Le osservazioni disponibili possono coprire soltanto pochi giorni. La tabella mostra le date effettive, le offerte, i negozi e i giorni per offerta. Il mese corrente non produce un indice. La mancata pubblicazione di un valore non significa prezzi invariati.</p>'+table+'<h2>Metodo riproducibile</h2><p>Per ogni offerta e data UTC usiamo l’ultimo prezzo disponibile osservato, soltanto se positivo, coerente con minimo e massimo giornalieri e associato a disponibilità esplicita. La data del recupero deve coincidere con il giorno. I duplicati ambigui sono esclusi. La media mensile è la media aritmetica di questi ultimi prezzi giornalieri, senza interpolare giorni mancanti.</p><p>Confrontiamo la stessa offerta dello stesso negozio in due mesi consecutivi: il suo titolo, variante, marca, GTIN e peso devono mantenere l’identità verificata nell’archivio. Occorrono almeno sette giorni validi per offerta in ciascun mese, dieci offerte abbinate e due negozi. Sono soglie editoriali minime, non una certificazione di rappresentatività. Un mese con sette giorni osservati non diventa un mese interamente coperto.</p><p>Per ogni coppia calcoliamo media del mese ÷ media del mese precedente; l’indice è 100 × la media geometrica di questi rapporti, tutti con lo stesso peso. Il riferimento 100 vale solo per il mese precedente di quella singola riga: non è una serie concatenata. Un valore 100 descrive assenza di variazione media nel pannello selezionato, non in tutto il mercato.</p><h2>Limiti da tenere presenti</h2><p>Si tratta di un indice descrittivo delle offerte seguite, non di inflazione, costo della vita o campione di tutti gli acquisti italiani. Non usiamo quantità vendute o quote di mercato. Lo stesso prodotto in negozi diversi costituisce offerte distinte. Le categorie sono quelle dichiarate nel catalogo, non classi di equivalenza nutrizionale.</p><p>La disponibilità riguarda l’ultimo recupero del giorno e non garantisce l’acquisto in ogni momento. La spedizione, le condizioni personali, gli abbonamenti e i vantaggi riservati non sono compresi. Il pannello include solo identità ancora verificabili nel catalogo attuale: eliminazioni, cambi di ricetta e nuovi negozi possono modificare il campione, introducendo distorsioni di selezione. Confronta sempre anche la copertura.</p><p>L’archivio corrente conserva al massimo 180 giorni; il bordo iniziale può tagliare un mese. I risultati sono ricalcolati con i dati conservati, non sono bollettini storici immutabili. Non deduciamo tendenze da pochi giorni e non usiamo questi valori per certificare sconti dei venditori.</p><h2>Dati e fonti</h2><p><a href="data/price-observatory.json" download>Scarica i dati e i pannelli di calcolo JSON</a>. Gli identificatori delle offerte si possono ricondurre al <a href="data/catalog.json.gz">catalogo pubblico</a>; l’archivio delle rilevazioni è <a href="data/price-history.json.gz">disponibile in formato gzip</a>. Nessun dato personale è incluso. <a href="chi-siamo.html">Metodo e fonti dei negozi</a> · <a href="leggere-storico-prezzi.html">Come leggere lo storico</a> · <a href="confronta-cibo.html">Confronta le offerte attuali</a>.</p></div></section>'
    return page(template,'osservatorio-prezzi','Osservatorio prezzi per animali: dati e metodo','Rilevazioni mensili del catalogo con copertura esplicita e indice soltanto su offerte comparabili, senza dati storici inventati.',body)


def build():
    catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    history=json.loads(gzip.decompress((ROOT/'site/data/price-history.json.gz').read_bytes()))
    data=calculate(catalog,history,dt.datetime.now(dt.timezone.utc).date())
    (ROOT/'site/data/price-observatory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (ROOT/'site/osservatorio-prezzi.html').write_text(render((ROOT/'site/chi-siamo.html').read_text(),data))
    print('Observed monthly coverage:',len(data['months']),'rows; published indices:',sum(r['index_previous_month_100'] is not None for r in data['months']))


if __name__=='__main__':build()
