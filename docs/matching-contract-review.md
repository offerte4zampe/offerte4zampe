# Contratto matching — join espliciti e sospensioni di confronto revisionate

Il controllo distingue il cambiamento intenzionale delle identità dalle regressioni estranee, conservando tutti gli assert del workflow precedente.

1. Base reale: main con resolver originale.
2. Head con resolver comune: tutto il codice PR, sostituendo `automation/name_matching.py` e la policy delle sospensioni di confronto con le versioni base; se la base non ha ancora tale policy, si usa una policy vuota. Il gate legacy conserva catalogo/storico/sitemap byte-identici, offerte/prodotti uguali, HTML e sitemap XML identici.
3. Head reale: codice PR senza sostituzioni, confrontato con le identità attese applicando esclusivamente le coppie esplicite di `tests/matching-join-manifest.json` al resolver base. Il modello atteso non apprende coppie dal risultato head. Un quarto albero temporaneo materializza questo modello per confrontare HTML, sitemap e shard.

Tutti i campi commerciali non derivati vengono confrontati per ID e impronta, inclusi prezzo, disponibilità, GTIN, quantità, URL e URL affiliato. L'intero risultato `offers/products/registry`, compresi i campi derivati, deve coincidere con l'oracle esplicito. HTML, sitemap, shard canonici, route e `_redirects` sono confrontati; lo storico resta byte-identico. Il Worker viene eseguito in memoria sui cataloghi rigenerati: stato 302, Location identica byte per byte e noindex/nofollow, senza richieste ai merchant, redirect seguiti o telemetria. Il fallback delle offerte indisponibili è coperto dall'equivalenza delle route/identità attese e dai test negativi esistenti del Worker.

Il contratto usa un unico clock UTC della verifica, non anteriore all’ultima decisione di sospensione del manifest di test; la data pubblicata dello snapshot resta distinta. Usa `PRICE_TRACKING_ENABLED=false` nei soli processi locali. Il gate legacy conserva il proprio test offline dello storico non Amazon con flag locale attivo. Nessuna configurazione di produzione viene modificata.

## Manifest e revisione merchant

Il manifest corrente contiene **15 identità commerciali revisionate indipendentemente**, non le sole 13 previsioni iniziali. Comprende le due coppie aggiuntive sotto indicate e comprende Trainer Anatra dopo la disambiguazione del produttore. Il job `merchant-review` richiede revisore, prove su due merchant, identificativi esatti e attributi di vendita. Ogni prova è vincolata all'impronta di merchant, titolo, marca, variante, URL, GTIN/feed GTIN normalizzati, SKU e quantità della riga catalogo: un cambio di prezzo non annulla la verifica di identità, un cambio di confezione sì. L’URL della prova deve riferirsi al prodotto e merchant esatti; le API Shopify `.js` devono dichiarare l’ID variante osservato, mentre le pagine HTML devono selezionarlo nella query. Prove future, più vecchie di 30 giorni, duplicate o riferite a un'altra offerta sono respinte. Cambiare soltanto `status` non basta. Non esistono skip per etichette o bypass dei check.

L'approvazione riguarda l'identità commerciale e la confezione pubblicata, non la certificazione fisica del lotto o l'identità chimica delle formulazioni. Royal Canin Sensible33 400g ha EAN e variante esatti coerenti, con una differenza nelle descrizioni degli ingredienti conservata come segnalazione. Per GranMix Canarini la composizione completa non è pubblicata da entrambi i merchant: il limite è dichiarato, pur avendo identificazione di linea/specie/formato e variante esatta.

Nello snapshot del 13 novembre erano emersi due join aggiuntivi non previsti, perché le sorgenti Isola erano nuove rispetto al 12 novembre:

| Sorgente | Controparte | Prodotto |
|---|---|---|
| isola-dei-tesori:000120162 | bauzaar:56962032435525 | Piccoli Amici Pellet Conigli Nani Adulti 2,5 kg |
| isola-dei-tesori:000120164 | bauzaar:56962032140613 | Piccoli Amici Pellet Gourmet Conigli Nani Adulti 800 g |

Le due coppie sono state ora verificate sui rispettivi SKU Isola e ID variante Shopify, con formato totale, specie/età e ricetta pubblicata coerenti. Sono entrate nel manifest soltanto dopo questa revisione; la coincidenza delle firme da sola non era sufficiente.

Il confronto Isola `000141050` / Animaliapet `47739940831575` era sospeso per ingredienti alla trota nella descrizione Animaliapet. Il selettore ufficiale Natural Trainer ha poi associato esplicitamente EAN `8059149430225`, presente nella variante merchant esatta, alla variante selezionata `1000062-3000116-965694`: Anatra, gatto adulto sterilizzato, secco, 1,500 kg. Questa prova aggiuntiva consente l'approvazione dell'identità commerciale. Resta il flag grave `description_recipe_contradiction`: non propagare quegli ingredienti né affermare composizioni identiche. La cronologia della sospensione è conservata nelle evidenze. Nessuna whitelist o blacklist di ID è stata introdotta nella logica di produzione.

Gli snapshot successivi sono sempre ricalcolati: il gate salva il delta effettivo. Una coppia già soddisfatta in baseline da GTIN uguali viene trattata come operazione nulla, mantenendo i vincoli di quantità/marca e il rifiuto dei GTIN discordanti.

## Ricetta e variante nei suffissi del titolo

La firma non tronca più tutto il testo dopo “- Cibo”, “- Lettiera” o “- Dieta veterinaria”. Quel suffisso può contenere una ricetta, secco/umido, una fragranza o una destinazione veterinaria. Vengono eliminate soltanto le parole generiche già previste nella normalizzazione; gli attributi protetti restano nella firma.

Prima della correzione quattro casi negativi venivano uniti erroneamente: pollo/trota, secco/umido, talco/lavanda e Renal/Struvite. I test li tengono separati e conservano anche un caso positivo di ricetta esattamente equivalente con parole commerciali diverse. Sullo snapshot reale confrontato, la correzione non cambia il numero dei join della PR; protegge il comportamento da questo difetto riproducibile.

## Esecuzione

- `python -m unittest discover -s tests`
- `python automation/check_d1_activation.py --prepare-build` prepara soltanto la fixture locale negata per default.
- `node --test tests/test_*.mjs tests/amazon_*.test.cjs`
- `python tests/check_matching_snapshot_contract.py --base-ref origin/main --output matching-contract-result.json`
- `python tests/check_matching_merchant_review.py` verifica le sole coppie approvate e le rispettive osservazioni; la review di una coppia esclusa non viene simulata come approvata.

Il risultato tecnico non chiude P0 né autorizza merge/deploy. Anche se il delta non coincide, il controllo esegue le verifiche indipendenti successive e salva le differenze e i risultati. La PR rimane bloccata quando il resolver effettua un'unione non approvata. Il rollback è il revert dei soli commit del ramo; il merge locale di aggiornamento main è separato. Nessun prezzo, stock, link affiliato, GTIN o flag di produzione viene riscritto da questa revisione.


## Sospensioni manuali di confronti incerti (P0)

Il contratto ammette anche le due sospensioni revisionate di PetUp Bauzaar e
Robofood WebPet, dichiarate indipendentemente in
`tests/matching-review-hold-manifest.json`. Questo manifest di test contiene ID,
merchant e metadati esatti della decisione: non apprende gli ID né il contenuto
atteso dall'output head. La configurazione di produzione deve coincidere con
questa decisione; anche una voce extra dormiente con ID assente dallo snapshot
è respinta. Cambiare solo il manifest di produzione non amplia l'oracolo.

L'albero common mantiene resolver e policy della base (vuota se non esiste).
Restano integralmente gli assert legacy di byte, offerte, prodotti, HTML e
sitemap. Il quarto albero oracle disattiva la policy di produzione: il suo
loader viene sostituito da una funzione vuota e la build riceve una policy
vuota. Un mapper di test separato esclude gli ID sospesi dal resolver originale
e assegna esclusivamente a questi `['unattached', offer_id]`. I metadati derivati
vengono poi applicati dal manifest di test; nessuna funzione di produzione che
sceglie o valida le sospensioni viene usata per predire quelle attese.

Il delta autorizzato è l'unione dei join espliciti ancora non soddisfatti nella
base e degli ID sospesi che devono cambiare identità. Un caso già isolato nella
base è una operazione nulla. `comparison_review` è solo un campo derivato: ciò
non esenta prezzi, stock, GTIN, quantità, URL e target affiliati dal confronto
rigoroso. L'intero output offers/products/registry e tutti gli artefatti protetti
devono ancora coincidere con l'oracle. I negativi rifiutano sospensioni aggiuntive,
ID nuovi o sconosciuti, perdita della sospensione, metadati non approvati e
modifiche ai campi commerciali della riga sospesa.
