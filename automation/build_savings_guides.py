"""Editorial guides with reproducible current catalog examples, never invented prices."""
import datetime as dt
import gzip
import hashlib
import json
import math
import re
from html import escape as h
from pathlib import Path
try:
    from .monitor_shipping_rules import report as shipping_report, parse as shipping_instant
    from .build_product_pages import page, fresh
    from .build_matched_pages import groups, merchant_url, product_label, slug_for
except ImportError:
    from monitor_shipping_rules import report as shipping_report, parse as shipping_instant
    from build_product_pages import page, fresh
    from build_matched_pages import groups, merchant_url, product_label, slug_for

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://offerte4zampe.it/'
REVIEW = '2026-10-20'


def eligible(o, now):
    return (fresh(o, now) and o.get('available') is True and isinstance(o.get('price'), (int,float))
            and math.isfinite(o['price']) and o['price'] > 0 and isinstance(o.get('weight_kg'), (int,float))
            and math.isfinite(o['weight_kg']) and o['weight_kg'] > 0 and str(o.get('url','')).startswith('https://'))


def food_examples(offers, now):
    rows = sorted((o for o in offers if eligible(o, now)
        and re.search(r'crocchett|alimento secco|cibo secco',o.get('category',''),re.I)
        and re.search(r'cane|cani|\bdog\b',o['title']+' '+o.get('category',''),re.I)
        and not re.search(r'veterinar|renal|diabet|medicat|integrator|farmac|diet',o['title']+' '+o.get('category',''),re.I)),
        key=lambda o:(o['title'].casefold(),o['id']))
    picked=[]; merchants=set()
    for o in rows:
        if o['merchant_id'] not in merchants:
            picked.append(o);merchants.add(o['merchant_id'])
        if len(picked)==3:break
    return picked


def litter_examples(offers, now):
    candidates=groups([o for o in offers if eligible(o,now)])
    choices=[(key,rows) for key,rows in candidates.items() if all('lettier' in (o['title']+' '+o.get('category','')).casefold() for o in rows)]
    return sorted(choices,key=lambda item:(product_label(item[1][0]).casefold(),item[0]))[:2]


def money(value): return f'{value:.2f}'.replace('.',',')+' €'


def source_link(o):
    return f'<a class="product-title-link" href="{h(merchant_url(o),quote=True)}" rel="{"sponsored noopener noreferrer" if o.get("affiliate_url") else "noopener noreferrer"}">{h(product_label(o))}</a>'


def document(template, slug, title, description, content, now):
    body=f'<section class="pagehero"><div class="wrap"><nav aria-label="Percorso"><a href="index.html">Home</a> / <a href="guide-risparmio.html">Guide al risparmio</a></nav><h1>{h(title)}</h1><p>{h(description)}</p><p class="micro">A cura della redazione Offerte a 4 Zampe · metodo rivisto il {REVIEW} · esempi aggiornati il <time datetime="{h(now.isoformat(),quote=True)}">{h(now.isoformat()[:16].replace("T"," "))} UTC</time>.</p></div></section><section class="section"><div class="wrap content">{content}<h2>Fonti, limiti e aggiornamento</h2><p>Gli esempi vengono dai feed ufficiali e cataloghi pubblici importati, con prezzo, peso netto e data per ogni riga. La selezione è alfabetica e alterna i negozi, senza dipendere dalle commissioni. Non rappresenta tutto il mercato. I calcoli non sono test nutrizionali o consigli veterinari.</p><p>I prezzi sono rilevazioni datate e la spedizione è esclusa dalle tabelle. Controlla sempre ricetta, confezione, disponibilità e totale nel negozio. I link Bauzaar e Isola dei Tesori possono generare una commissione senza costi aggiuntivi per te. <a href="chi-siamo.html">Metodo e fonti dei cataloghi</a> · <a href="correzioni.html">Controlli e correzioni</a>.</p><p><a href="guide-risparmio.html">Altre guide pratiche</a> · <a href="confronta-cibo.html">Cerca il tuo prodotto</a> · <a href="carrello-risparmio.html">Confronta la lista della spesa</a>.</p></div></section>'
    out=page(template,slug,title,description,body)
    schema={'@context':'https://schema.org','@graph':[{'@type':'Article','headline':title,'description':description,'dateModified':now.isoformat(),'author':{'@type':'Organization','name':'Redazione Offerte a 4 Zampe','url':BASE+'chi-siamo'},'mainEntityOfPage':BASE+slug},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':BASE+url} for i,(name,url) in enumerate([('Home',''),('Guide al risparmio','guide-risparmio'),(title,slug)])]}]}
    return out.replace('</head>','<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace('</',r'<\/')+'</script></head>')


def food_content(offers,now):
    rows=[]
    for o in food_examples(offers,now):
        unit=o['price']/o['weight_kg'];day=unit*.25
        rows.append(f'<tr><td>{source_link(o)}<br>{h(o["merchant"])}</td><td>{o["weight_kg"]:g} kg</td><td>{money(o["price"])}</td><td>{money(unit)}/kg</td><td>{money(day)}</td><td>{money(day*30)}</td><td>{h(o["checked_at"][:16].replace("T"," "))} UTC</td></tr>')
    table='<p>Nessun esempio recente con peso netto verificabile: usa il comparatore per controllare il catalogo.</p>'
    if rows: table='<div class="guide-table" tabindex="0" role="region" aria-label="Esempi di costo con razione ipotetica"><table><caption>Razione ipotetica uguale di 250 g/giorno, spedizione esclusa</caption><thead><tr><th>Prodotto e fonte</th><th>Peso netto</th><th>Confezione</th><th>Costo/kg</th><th>Al giorno</th><th>Per 30 giorni</th><th>Rilevazione</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    return '<h2>Il prezzo del sacco non basta</h2><p>Il costo mensile dipende da tre dati: prezzo della confezione, peso netto e grammi effettivamente consumati al giorno. Un sacco economico può contenere meno prodotto; un prezzo al kg inferiore può richiedere un esborso iniziale maggiore. Separare questi aspetti aiuta a confrontare la spesa senza trasformare un prezzo in un giudizio sulla qualità dell’alimento.</p><h2>La formula da usare sulla tua confezione</h2><p>Prezzo/kg = prezzo della confezione ÷ kg netti. Costo giornaliero = prezzo/kg × grammi al giorno ÷ 1.000. Per una stima su 30 giorni moltiplica il risultato non arrotondato per 30. La spesa di spedizione va aggiunta una volta all’ordine, non a ogni porzione.</p><p>Usa il peso netto dichiarato: il peso di spedizione comprende altri elementi e non misura quanto cibo acquisti. Se il formato non è verificabile, il sito evita il prezzo/kg. Non ricavare una razione dal prezzo: leggi l’etichetta e segui le indicazioni del veterinario per il tuo animale.</p><h2>Esempi con prezzi realmente rilevati</h2><p>La tabella usa una quantità ipotetica di 250 g al giorno soltanto per rendere riproducibile il calcolo. Non è una razione consigliata né una previsione per un cane di una certa taglia. Le ricette elencate sono diverse: la stessa quantità non dimostra equivalenza energetica o nutrizionale.</p>'+table+'<h2>Dal consumo al denaro da spendere</h2><p>Il costo di 30 giorni descrive il prodotto consumato nell’ipotesi scelta. Il pagamento al negozio riguarda invece confezioni intere: puoi dover comprare un sacco oggi e usarne una parte il mese prossimo. Per il budget considera entrambi i numeri e controlla spazio disponibile, conservazione e tempi indicati dal produttore. Comprare più confezioni solo per raggiungere una soglia di spedizione può aumentare la spesa subito necessaria.</p><h2>Quando due alimenti si possono confrontare</h2><p>Per cercare lo stesso prodotto tra negozi usa codice GTIN, marca e formato, poi verifica la ricetta sull’etichetta. Il solo nome commerciale può nascondere differenze. Per confrontare alimenti diversi, il costo giornaliero ha senso soltanto con le rispettive razioni adatte al tuo animale: non usare una porzione uguale come prova di convenienza nutrizionale.</p><h2>Fai il calcolo con i tuoi dati</h2><p>Nel comparatore apri il calcolo giornaliero dell’offerta e inserisci la razione che hai verificato. Il campo parte vuoto: non assegniamo una dieta automaticamente. Per quantità e spedizione usa la <a href="carrello-risparmio.html">lista risparmio</a>, che confronta ordini completi solo quando assortimento e condizioni sono stimabili.</p><a class="btn" href="/calcolatore#manual-tool">Apri il calcolatore →</a>'


def litter_content(offers,now):
    tables=[]
    for key,rows in litter_examples(offers,now):
        lines=[]
        for o in sorted(rows,key=lambda o:(o['merchant'].casefold(),o['id'])):
            lines.append(f'<tr><td>{h(o["merchant"])}</td><td>{source_link(o)}</td><td>{o["weight_kg"]:g} kg</td><td>{money(o["price"])}</td><td>{money(o["price"]/o["weight_kg"])}/kg</td><td>{h(o["checked_at"][:16].replace("T"," "))} UTC</td></tr>')
        tables.append(f'<h3>Codice GTIN {h(key[0])} · {h(rows[0]["brand"])}</h3><div class="guide-table" tabindex="0" role="region" aria-label="Prezzi dello stesso formato di lettiera"><table><caption>Stesso GTIN, marca e peso netto dichiarati; spedizione esclusa</caption><thead><tr><th>Negozio</th><th>Prodotto</th><th>Formato</th><th>Confezione</th><th>Costo/kg</th><th>Rilevazione</th></tr></thead><tbody>{"".join(lines)}</tbody></table></div><p><a href="{slug_for(key)}.html">Apri tutte le offerte dello stesso formato</a>.</p>')
    examples=''.join(tables) or '<p>Non sono disponibili confronti recenti con identità e peso sufficienti. Non accostiamo automaticamente lettiere con nomi simili.</p>'
    return '<h2>Parti dalla confezione esatta</h2><p>Per confrontare una lettiera controlla materiale, variante, profumazione e formato. Due confezioni dello stesso marchio possono essere prodotti diversi. Nel catalogo raggruppiamo soltanto GTIN, marca e peso netto coincidenti; questo controllo non sostituisce la lettura dell’etichetta, ma evita di unire offerte solo per somiglianza del nome.</p><h2>Litri e chilogrammi misurano cose diverse</h2><p>Il litro esprime un volume, il chilogrammo una massa. Non convertiamo automaticamente 10 litri in 10 kg: materiali diversi possono avere pesi diversi a parità di volume. Quando il catalogo dichiara entrambi, manteniamo il peso netto esplicito. Se ci sono solo litri, il prezzo/kg resta non disponibile. Anche il peso di spedizione non è un sostituto del contenuto netto.</p><h2>Due confronti tratti dal catalogo</h2><p>Questi esempi sono selezionati in ordine alfabetico tra i gruppi recenti di lettiere, senza privilegiare commissioni o differenze di prezzo. L’ordine dei negozi è alfabetico. Non sono una classifica di qualità o una promessa sul negozio più economico dopo la spedizione.</p>'+examples+'<h2>Il totale cambia con la lista della spesa</h2><p>Una confezione dal prezzo più basso può appartenere a un ordine con spedizione maggiore. Se compri più prodotti nello stesso negozio, la soglia di gratuità e l’eventuale peso massimo si applicano all’ordine. Sommare una spedizione a ogni prodotto sovrastima il totale; ignorarla sottostima quanto pagherai. Località particolari, servizi aggiuntivi e condizioni non verificate possono impedire una stima affidabile.</p><p>La <a href="carrello-risparmio.html">lista risparmio</a> applica la spedizione una volta al subtotale e confronta soltanto gli assortimenti completi con identità verificabile. Se un negozio ha una parte dei prodotti richiesti, non mostriamo quel subtotale come alternativa all’intera spesa. Le tariffe hanno una data di verifica e il checkout resta il riferimento finale.</p><h2>Prova prima una quantità realistica</h2><p>Valuta quante confezioni ti servono e quanto spazio hai prima di aggiungere articoli per superare una soglia. Il prezzo/kg è utile per confrontare formati verificati, ma non dimostra quanto durerà una lettiera: durata e consumo dipendono anche dall’uso e dalle indicazioni del produttore. Non traduciamo quindi il prezzo in un costo mensile universale.</p><h2>Una verifica rapida prima del pagamento</h2><p>Apri la scheda del negozio e ricontrolla nome completo, variante, quantità selezionata, prezzo della confezione e spese per la tua destinazione. I multipack con base del prezzo non chiara vengono esclusi finché la quantità non è verificata. Se trovi una discrepanza, usa la segnalazione accanto al prezzo: la bozza mostra i dati dell’offerta prima di aprire il tuo programma email.</p><a class="btn" href="confronta-cibo.html?q=lettiera">Cerca una lettiera nel comparatore →</a>'


GUIDES = [('costo-crocchette-cane','Quanto costano le crocchette al mese?','Prezzo/kg e costo giornaliero con esempi reali e una razione modificabile: separa consumo, confezioni e spedizione.',food_content),('confrontare-prezzi-lettiere','Come confrontare i prezzi delle lettiere','Formati in kg e litri, stesso prodotto e spesa complessiva: esempi rilevati dal catalogo e controlli prima del checkout.',litter_content)]


def pack_content(offers, now):
    rows=[]
    for o in food_examples(offers, now):
        rows.append(f'<tr><td>{source_link(o)}<br>{h(o["merchant"])}</td><td>{o["weight_kg"]:g} kg</td><td>{money(o["price"])}</td><td>{money(o["price"]/o["weight_kg"])}/kg</td><td>{h(o["checked_at"][:16].replace("T"," "))} UTC</td></tr>')
    table='<p>Nessun esempio recente con peso netto disponibile. Il metodo resta utilizzabile sulla confezione del negozio.</p>'
    if rows:
        table='<div class="guide-table" tabindex="0" role="region" aria-label="Prezzo della confezione e prezzo al chilo"><table><caption>Esempi di lettura del prezzo, ricette diverse e spedizione esclusa</caption><thead><tr><th>Prodotto e fonte</th><th>Peso netto</th><th>Confezione</th><th>Prezzo/kg</th><th>Rilevazione</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    return ('<h2>Due numeri per due decisioni diverse</h2><p>Il prezzo della confezione indica quanto paghi per portare a casa quel formato. Il prezzo al chilo serve a capire quanto costa una quantità uguale di prodotto. Leggerli insieme evita di scegliere un sacco soltanto perché il numero più grande sulla scheda sembra basso. Il formato più conveniente al chilo può richiedere più denaro subito; quello con l’esborso minore può costare di più per la stessa quantità.</p>'
        '<h2>Rifai il conto prima di confrontare</h2><p>Dividi il prezzo della confezione per i chilogrammi netti dichiarati. Se il peso è espresso in grammi, dividilo prima per 1.000. Usa il risultato non arrotondato per i calcoli successivi e arrotonda soltanto il valore mostrato. Il peso del collo usato dal corriere non misura il contenuto acquistato: se manca il peso netto, lascia il confronto al chilo in sospeso.</p>'
        '<h2>Esempi attuali: dalla confezione al chilo</h2><p>Le righe seguenti mostrano come leggere entrambi i valori nel catalogo. Sono prodotti e ricette differenti, selezionati alfabeticamente alternando i negozi: non costituiscono una graduatoria e non dimostrano che un alimento possa sostituirne un altro.</p>'+table+
        '<h2>La stessa marca non basta</h2><p>Prima di cercare lo stesso articolo in un altro negozio, controlla il nome completo, la ricetta, la fase di vita dichiarata e il formato selezionato. Il nostro confronto esatto richiede un GTIN valido, una marca e un peso netto coincidenti. Se cambi dimensione del sacco, può cambiare anche il codice: le offerte restano separate. Un’identità incerta non diventa verificata perché i nomi delle schede si assomigliano.</p>'
        '<h2>Attenzione al selettore e ai multipack</h2><p>Una pagina può contenere più formati mentre il titolo visibile descrive soltanto quello iniziale. Controlla quale opzione è selezionata quando apri il negozio e quale quantità finisce nel carrello. Per un multipack servono numero di confezioni, contenuto netto di ciascuna e conferma che il prezzo riguardi l’intero pacco. Se uno di questi dati manca, non moltiplicare il formato per ricostruire un prezzo apparentemente conveniente. Escludiamo i multipack con base del prezzo non verificata.</p>'
        '<h2>Aggiungi la spedizione al livello dell’ordine</h2><p>Il prezzo/kg della tabella esclude la spedizione. Per sapere quanto spendi davvero, scegli quantità realistiche e confronta il totale della lista: prodotti più spedizione applicata una volta. Una soglia gratuita non rende gratuito il prodotto aggiunto per raggiungerla. Nel carrello risparmio i negozi con assortimento incompleto o condizioni non verificabili non vengono presentati come alternativa completa con un totale certo.</p>'
        '<h2>Il sacco grande entra nel tuo budget?</h2><p>Controlla lo spazio disponibile e le indicazioni di conservazione del produttore. Il prezzo/kg non dimostra quanto durerà il prodotto né quale razione sia adatta al tuo animale. Se conosci già la razione, il calcolatore giornaliero traduce il prezzo e il peso in costo del consumo; il pagamento resta legato a confezioni intere. Puoi così valutare separatamente esborso immediato e consumo previsto.</p>'
        '<p>Prima del pagamento ricontrolla formato, quantità, prezzo e disponibilità nel negozio: una rilevazione datata non garantisce il totale al checkout. Per approfondire il consumo consulta la <a href="costo-crocchette-cane.html">guida al costo giornaliero e mensile</a>; per il pagamento usa la <a href="carrello-risparmio.html">lista risparmio</a>.</p>')


GUIDES.append(('prezzo-confezione-o-prezzo-kg','Prezzo della confezione o prezzo al kg: cosa confrontare','Esempi dal catalogo per leggere il costo del sacco, verificare formati e multipack e distinguere prezzo unitario da spesa totale.',pack_content))


def verified_shipping_rules(rules, now):
    """Select current evidence with the existing shipping monitor's classification."""
    now = now.replace(tzinfo=now.tzinfo or dt.timezone.utc)
    result = []
    for evidence in shipping_report(rules, now, expected=())['merchants']:
        if evidence['quote_status'] != 'requires_offer_check':
            continue
        merchant = evidence['merchant']
        rule = rules['merchants'][merchant]
        fee = rule.get('fee')
        if (rule.get('status') not in (None, 'verified')
                or not isinstance(fee, (int, float)) or isinstance(fee, bool)
                or not math.isfinite(fee) or fee < 0
                or not str(rule.get('source', '')).startswith('https://')):
            continue
        try:
            if (rule.get('valid_from') is not None and shipping_instant(rule['valid_from']) > now
                    or rule.get('valid_to') is not None and shipping_instant(rule['valid_to']) <= now):
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        result.append((merchant, rule, evidence['checked_at']))
    return sorted(result, key=lambda row: row[1].get('name', row[0]).casefold())


def shipping_content(offers, now, rules=None):
    if rules is None:
        rules=json.loads((ROOT/'site/data/shipping-rules.json').read_text())
    rows=[]
    for merchant, rule, checked in verified_shipping_rules(rules, now):
        rows.append(f'<tr data-shipping-merchant="{h(merchant,quote=True)}"><td>{h(rule.get("name",merchant))}</td><td>{h(rule.get("note","Condizioni non disponibili"))}</td><td><a href="{h(rule["source"],quote=True)}" rel="noopener noreferrer">Condizioni ufficiali</a></td><td>{h(checked)}</td></tr>')
    table='<p>Nessuna regola di spedizione con verifica e scadenza valide: consulta il checkout dei negozi per le tariffe attuali.</p>'
    if rows:
        table='<div class="guide-table" tabindex="0" role="region" aria-label="Condizioni di spedizione verificate"><table><caption>Consegna standard Italia continentale: soglie esatte dubbie, peso mancante o oltre i limiti e servizi esclusi lasciano il totale ignoto</caption><thead><tr><th>Negozio</th><th>Condizioni e limiti</th><th>Fonte</th><th>Verifica</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    scope='<p class="micro">'+h(rules.get('scope',''))+'</p>' if rules.get('scope') else ''
    return (scope+'<h2>La soglia gratuita è una condizione dell’ordine</h2><p>Quando un negozio propone la spedizione gratuita oltre un importo minimo, il vantaggio riguarda il costo della consegna. Per capire se conviene aggiungere un prodotto devi confrontare due pagamenti completi: la lista che ti serve con la sua spedizione, e la lista ampliata con la nuova spedizione. Raggiungere la soglia non dimostra automaticamente un risparmio.</p>'
        '<h2>Il confronto da fare senza inventare un carrello</h2><p>Indica con S il subtotale degli articoli necessari e con F la consegna prevista per quella lista. La prima alternativa costa S + F. Se aggiungi un articolo da A euro e la consegna diventa gratuita, la seconda costa S + A. La differenza è A − F: quando A è maggiore di F, paghi di più oggi. Se la consegna non diventa gratuita, va aggiunta anche la nuova tariffa. Questo calcolo confronta l’esborso; l’utilità dell’articolo aggiunto rimane una tua scelta.</p>'
        '<h2>Le condizioni che abbiamo effettivamente controllato</h2><p>La tabella riprende il registro usato dal carrello risparmio, con fonte e data. Mantiene esplicite le soglie ambigue e le informazioni discordanti. Una tariffa non verificata non viene sostituita con zero. Ogni negozio compare solo fino alla scadenza della sua verifica. Le note sono condizioni, non preventivi: il totale resta ignoto alla soglia esatta dubbia, con peso di spedizione mancante o oltre il limite e per destinazioni o servizi esclusi. Il checkout resta il riferimento per la tua destinazione.</p>'+table+
        '<h2>“Da” e “oltre” non sono la stessa soglia</h2><p>Se le condizioni dicono “da” un certo importo, la soglia può includere quell’importo esatto. “Oltre” richiede invece di superarlo. Quando il testo del negozio non chiarisce il punto di confine, il nostro calcolo lascia il totale non disponibile per quel caso. Non aggiungere un centesimo immaginario o una quantità non selezionabile per risolvere il confronto: verifica i prodotti e le condizioni reali del tuo ordine.</p>'
        '<h2>Controlla anche peso e destinazione</h2><p>La gratuità può avere un limite di peso o escludere alcune località e servizi. Il peso netto serve per il prezzo/kg del prodotto; il peso di spedizione serve per i limiti del corriere. Sono dati diversi. Una confezione con peso netto noto non basta a dimostrare che un ordine rientri nel limite logistico. Se manca il peso necessario o la destinazione richiede un supplemento non noto, evita di considerare certo il totale stimato.</p>'
        '<h2>Confronta la stessa lista tra negozi</h2><p>Salva gli articoli che ti servono nella <a href="carrello-risparmio.html">lista risparmio</a> e imposta le quantità. Il confronto completo richiede la stessa identità del prodotto e lo stesso formato per ogni voce. Un negozio che dispone solo di parte della lista non è un’alternativa equivalente, anche se il suo subtotale è più basso. La spedizione si applica una volta al singolo ordine, non una volta per ciascun prodotto.</p>'
        '<h2>Prima di aggiungere una scorta</h2><p>Considera se avresti comunque comprato il prodotto, quando prevedi di usarlo, lo spazio disponibile e le indicazioni di conservazione sulla confezione. Una scorta può anticipare una spesa futura ma aumenta il pagamento immediato. Non scegliere ricette diverse soltanto per raggiungere la gratuità: il confronto del costo non certifica equivalenza nutrizionale. Per distinguere contenuto e costo unitario leggi anche la <a href="prezzo-confezione-o-prezzo-kg.html">guida a confezioni e prezzo/kg</a>.</p>'
        '<p>Controlla infine il carrello del negozio: quantità selezionata, eventuali vincoli del codice promozionale, consegna per il tuo CAP e importo da pagare. Il sito mostra rilevazioni e regole datate, senza promettere che il checkout resti invariato.</p>')


GUIDES.append(('spedizione-gratuita-conviene','Spedizione gratuita: conviene raggiungere la soglia?','Confronta l’esborso della lista con e senza articoli aggiunti, usando soglie, limiti di peso e condizioni ufficiali datate.',shipping_content))



def observed_examples(offers, now, history):
    examples=[]
    cutoff=now.date()-dt.timedelta(days=179)
    for o in food_examples(offers, now):
        identity=hashlib.sha256(json.dumps([o.get(k) for k in ('merchant_id','title','variant','brand','gtin','weight_kg')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        if history.get('identities',{}).get(o['id'])!=identity:
            continue
        days={}
        for item in history.get('offers',{}).get(o['id'],[]):
            try:
                day=dt.date.fromisoformat(item['day'])
                values=[item[k] for k in ('low','last','high')]
                if not cutoff<=day<=now.date() or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values):
                    continue
                if not values[0]<=values[1]<=values[2]:
                    continue
                if day in days:
                    days[day]=(min(days[day][0],values[0]),max(days[day][1],values[2]))
                else:
                    days[day]=(values[0],values[2])
            except (ValueError,KeyError,TypeError):
                continue
        if days:
            examples.append((o,{'days':len(days),'first':min(days).isoformat(),'last':max(days).isoformat(),'low':min(v[0] for v in days.values()),'high':max(v[1] for v in days.values())}))
    return examples


def history_content(offers, now, history=None):
    if history is None:
        path=ROOT/'site/data/price-history.json.gz'
        try:
            history=json.loads(gzip.decompress(path.read_bytes())) if path.exists() else {}
        except (OSError,ValueError,EOFError):
            history={}
    rows=[]
    for o,stats in observed_examples(offers,now,history):
        rows.append(f'<tr><td>{source_link(o)}<br>{h(o["merchant"])}</td><td>{o["weight_kg"]:g} kg</td><td>{stats["days"]}</td><td>{h(stats["first"])} – {h(stats["last"])}</td><td>{money(stats["low"])}</td><td>{money(stats["high"])}</td></tr>')
    table='<p>Non ci sono ancora osservazioni con identità verificata da usare come esempio. Nessun prezzo minimo viene ricostruito.</p>'
    if rows:
        table='<div class="guide-table" tabindex="0" role="region" aria-label="Esempi di prezzi realmente osservati"><table><caption>Finestra massima 180 giorni, solo date raccolte e prezzi della confezione; spedizione esclusa</caption><thead><tr><th>Prodotto e fonte</th><th>Formato</th><th>Giorni osservati</th><th>Prima e ultima data UTC</th><th>Minimo osservato</th><th>Massimo osservato</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    return ('<h2>Un minimo ha senso insieme al periodo osservato</h2><p>Vedere un prezzo vicino al minimo può aiutare a valutare un acquisto, ma prima chiediti da quanti giorni quel prodotto viene seguito. Una sola giornata può produrre un minimo e un massimo identici: descrive ciò che abbiamo raccolto, senza dimostrare che il prezzo sia rimasto stabile nei mesi precedenti. Il nostro storico conserva soltanto rilevazioni effettive e non ricostruisce il passato.</p>'
        '<h2>Che cosa mostrano questi esempi</h2><p>La tabella riporta prodotti del catalogo recente con identità storica verificata. Il conteggio riguarda date distinte nella finestra di 180 giorni, anche quando nello stesso giorno sono stati recuperati più prezzi. Le righe sono scelte alfabeticamente alternando i negozi. Sono esempi di lettura dello storico e non una selezione di affari: ricette diverse non vengono considerate equivalenti.</p>'+table+
        '<h2>30, 90 e 180 giorni sono finestre, non promesse di copertura</h2><p>Nel comparatore apri “Storico prezzi osservati” sulla scheda e scegli il periodo. La finestra delimita le date che possono entrare nel riepilogo. Il numero di giorni osservati indica invece quante date abbiamo davvero a disposizione. Se il sito segue quel formato soltanto da poco, una finestra più lunga può mostrare gli stessi pochi punti. Gli intervalli senza dati rimangono vuoti: non rappresentano un prezzo pari a zero.</p>'
        '<h2>Più recuperi in una giornata</h2><p>Per ogni data conserviamo minimo e massimo recuperati, ultimo prezzo e disponibilità dell’ultimo recupero. Non è un archivio di ogni variazione intragiornaliera. Il minimo giornaliero può quindi differire dall’ultimo prezzo visibile. Inoltre, la disponibilità osservata per ultima non prova che ogni prezzo di quella giornata fosse acquistabile. Per comprare, verifica sempre la scheda e il carrello del negozio.</p>'
        '<h2>Resta sullo stesso prodotto e negozio</h2><p>Lo storico appartiene a una specifica offerta del negozio. Un codice interno riutilizzato per una nuova ricetta o un altro formato non deve ereditare i prezzi precedenti. Per questo controlliamo l’identità dichiarata, includendo titolo, variante, marca, GTIN e peso netto: se cambia, la serie riparte. Un grafico più corto può quindi dipendere anche da una correzione dell’identità, non soltanto da un prodotto appena importato.</p>'
        '<h2>Storico e confronto tra negozi rispondono a domande diverse</h2><p>Lo storico mostra come è variata l’offerta che abbiamo osservato nel tempo. Il confronto per GTIN, marca e peso netto mostra le offerte recenti dello stesso formato in negozi diversi. Un negozio può essere vicino al proprio minimo e costare comunque più di un altro oggi. Per scegliere, parti dal confronto attuale e aggiungi la spedizione della lista completa; usa lo storico come contesto.</p>'
        '<h2>Il minimo osservato non certifica uno sconto</h2><p>La nostra finestra di raccolta non dimostra quale prezzo precedente un venditore debba usare per annunciare una riduzione. Non trasformiamo quindi questi minimi in un prezzo barrato o in una percentuale promozionale. Anche il minimo su pochi giorni non è una previsione: non permette di stabilire quando il prodotto scenderà ancora o se tornerà disponibile a quel prezzo.</p>'
        '<p>Prova il dettaglio storico nel <a href="confronta-cibo.html">comparatore</a>, controlla la tabella delle date e poi verifica il totale nella <a href="carrello-risparmio.html">lista risparmio</a>. Se formato o prezzo non corrispondono, usa la segnalazione accanto all’offerta. Il registro <a href="correzioni.html">Correzioni</a> distingue gli interventi documentati dai sospetti ancora da verificare.</p>')


GUIDES.append(('leggere-storico-prezzi','Come leggere lo storico prezzi senza farsi ingannare','Minimi, massimi e giorni realmente osservati: esempi del catalogo per distinguere una finestra di ricerca da una serie storica completa.',history_content))



def identity_examples(offers, now):
    choices=groups([o for o in offers if eligible(o,now)])
    return sorted(choices.items(),key=lambda item:(product_label(item[1][0]).casefold(),item[0]))[:2]


def identity_content(offers, now):
    sections=[]
    for key,items in identity_examples(offers,now):
        rows=[]
        for o in sorted(items,key=lambda item:(item['merchant'].casefold(),item['id'])):
            rows.append(f'<tr><td><a class="product-title-link" href="{h(slug_for(key),quote=True)}.html">{h(product_label(o))}</a><br>{h(o["merchant"])}</td><td>{h(key[0])}</td><td>{h(o["brand"])}</td><td>{o["weight_kg"]:g} kg</td><td>{money(o["price"])}</td><td>{h(o["checked_at"][:16].replace("T"," "))} UTC</td></tr>')
        prices=[o['price'] for o in items]
        difference=money(max(prices)-min(prices))
        sections.append(
            f'<section aria-label="Confronto {h(product_label(items[0]),quote=True)}">'
            f'<h3>{h(product_label(items[0]))} · {items[0]["weight_kg"]:g} kg</h3>'
            f'<p>Due o più negozi con GTIN {h(key[0])}, marca e peso netto coincidenti. '
            f'Differenza fra i prezzi rilevati: <strong>{difference}</strong>, spedizione esclusa; '
            'non è un risparmio garantito al checkout.</p>'
            '<div class="guide-table" tabindex="0" role="region" aria-label="Prezzi dello stesso formato">'
            '<table><caption>Offerte della stessa identità dichiarata, in ordine alfabetico per negozio</caption>'
            '<thead><tr><th>Prodotto e fonte</th><th>GTIN</th><th>Marca</th><th>Peso netto</th><th>Prezzo</th><th>Rilevazione</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p><a class="btn secondary" href="{h(slug_for(key),quote=True)}.html">Apri il confronto aggiornato fra negozi →</a></p>'
            '</section>')
    table=''.join(sections) or '<p>Nessun esempio recente confrontabile in più negozi: i prodotti senza abbinamento certo restano separati.</p>'
    return ('<h2>Prima del prezzo controlla cosa stai comprando</h2><p>Due titoli simili possono descrivere ricette, quantità o confezioni diverse. Una foto uguale non basta: può raffigurare una linea intera oppure un formato diverso da quello selezionato. Prima di scegliere il prezzo più basso, verifica nome completo, variante, quantità netta e numero di unità nella scheda del negozio. Il nostro confronto economico non certifica equivalenza nutrizionale.</p>'
        '<h2>Gli identificatori che usiamo nel catalogo</h2><p>Per riunire offerte di negozi diversi richiediamo un GTIN con cifra di controllo valida, la stessa marca normalizzata e lo stesso peso netto dichiarato. Non correggiamo un codice mancante copiandolo da una foto o da un prodotto dal nome simile. La cifra di controllo verifica la struttura del numero: non garantisce da sola che il negozio lo abbia assegnato correttamente al prodotto.</p>'
        '<h2>Esempi leggibili, non una classifica di convenienza</h2><p>Queste righe provengono dal catalogo recente e disponibile al rilevamento. Il codice viene riportato per consentire un controllo, insieme a marca, peso, fonte e data. La selezione dei gruppi è alfabetica, non ordinata per commissione. I prezzi escludono la spedizione: una differenza fra righe non dimostra quale ordine completo costi meno.</p>'+table+
        '<h2>Il codice del negozio non è il codice del prodotto</h2><p>Il numero nella URL o nella scheda può essere un identificatore interno del venditore. Due negozi possono usare numeri diversi per lo stesso prodotto; lo stesso negozio può cambiare pagina mantenendo una parte del titolo. Non confrontare questi identificatori come se fossero GTIN. Quando manca il codice condiviso, puoi cercare e leggere le offerte, ma il sito non le unisce automaticamente in un confronto certo.</p>'
        '<h2>Nei multipack verifica entrambe le quantità</h2><p>Una vendita può comprendere più unità. Il peso di una singola busta e il peso totale del pacco non sono intercambiabili. Il codice mostrato può riferirsi alla singola unità oppure alla confezione venduta: non deduciamo quale dei due sia dal solo titolo. Se quantità e codice non sono sufficientemente chiari, teniamo separata l’offerta anziché moltiplicare una quantità ipotizzata. Controlla anche che il prezzo corrisponda alla variante effettivamente selezionata.</p>'
        '<h2>Che cosa fare se non trovi il confronto</h2><p>Prova il nome della linea e poi il formato nel <a href="confronta-cibo.html">comparatore</a>. L’assenza di un gruppo non significa che il prodotto sia venduto da un solo negozio: può mancare un dato, essere scaduta una rilevazione o essere diverso il formato importato. Non sostituire un prodotto nella lista solo per ottenere un risultato più economico. Usa la <a href="carrello-risparmio.html">lista risparmio</a> quando le identità dei tuoi articoli sono confermate.</p>'
        '<h2>L’ultimo controllo avviene nel negozio</h2><p>Apri la fonte e verifica ricetta, formato, numero di pezzi, disponibilità e importo nel carrello. I dati importati possono contenere errori: anche una coincidenza dei tre campi rimane un criterio documentato di abbinamento, non una garanzia assoluta. Se noti una discrepanza, usa “Prezzo sbagliato?” accanto all’offerta indicando il dato da correggere. Non occorre allegare informazioni sul pagamento o altri dati personali.</p>'
        '<p>Per confrontare taglie diverse senza confonderle leggi la <a href="prezzo-confezione-o-prezzo-kg.html">guida al prezzo della confezione e al costo/kg</a>. Per valutare un ordine intero consulta le <a href="spedizione-gratuita-conviene.html">condizioni di spedizione</a>: stesso prodotto e stesso pagamento completo sono due controlli distinti.</p>')


GUIDES.append(('stesso-prodotto-formato-gtin','Stesso prodotto o solo un nome simile? Controlla formato e GTIN','Esempi del catalogo per distinguere codice prodotto, formato e multipack prima di confrontare i prezzi tra negozi.',identity_content))


def build():
    now=dt.datetime.now(dt.timezone.utc)
    catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    template=(ROOT/'site/chi-siamo.html').read_text()
    for slug,title,description,render in GUIDES:
        (ROOT/f'site/{slug}.html').write_text(document(template,slug,title,description,render(catalog['offers'],now),now))
    links=''.join(f'<article class="panel"><h2><a href="{slug}.html">{h(title)}</a></h2><p>{h(description)}</p></article>' for slug,title,description,_ in GUIDES)
    body='<section class="pagehero"><div class="wrap"><h1>Guide pratiche al risparmio per cani e gatti</h1><p>Metodi riproducibili ed esempi del catalogo, con fonti, date e limiti. Nessuna classifica nutrizionale.</p></div></section><section class="section"><div class="wrap content">'+links+'<p><a href="confronta-cibo.html">Confronta prezzi</a> · <a href="osservatorio-prezzi.html">Osservatorio prezzi</a> · <a href="chi-siamo.html">Metodo editoriale</a>.</p></div></section>'
    (ROOT/'site/guide-risparmio.html').write_text(page(template,'guide-risparmio','Guide pratiche al risparmio per animali','Guide con esempi reali per confrontare confezioni, costo al kg e spese di spedizione.',body))


if __name__=='__main__':build()
