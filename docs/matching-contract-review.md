# PR99 — contratto matching e parità

Il controllo distingue il cambiamento intenzionale delle identità dalle regressioni estranee, conservando tutti gli assert del workflow precedente.

1. Base reale: main con resolver originale.
2. Head con resolver comune: tutto il codice PR, sostituendo soltanto `automation/name_matching.py` con la versione base. Il gate legacy conserva catalogo/storico/sitemap byte-identici, offerte/prodotti uguali, HTML e sitemap XML identici.
3. Head reale: codice PR senza sostituzioni, confrontato con le identità attese applicando esclusivamente le coppie esplicite di `tests/matching-join-manifest.json` al resolver base. Il modello atteso non apprende coppie dal risultato head. Un quarto albero temporaneo materializza questo modello per confrontare HTML, sitemap e shard.

Tutti i campi commerciali non derivati vengono confrontati per ID e impronta, inclusi prezzo, disponibilità, GTIN, quantità, URL e URL affiliato. L'intero risultato `offers/products/registry`, compresi i campi derivati, deve coincidere con l'oracle esplicito. HTML, sitemap, shard canonici, route e `_redirects` sono confrontati; lo storico resta byte-identico. Il Worker viene eseguito in memoria sui cataloghi rigenerati: stato 302, Location identica byte per byte e noindex/nofollow, senza richieste ai merchant, redirect seguiti o telemetria. Il fallback delle offerte indisponibili è coperto dall'equivalenza delle route/identità attese e dai test negativi esistenti del Worker.

Il contratto usa la data dello snapshot come clock e `PRICE_TRACKING_ENABLED=false` nei soli processi locali. Il gate legacy conserva il proprio test offline dello storico non Amazon con flag locale attivo. Nessuna configurazione di produzione viene modificata.

## Manifest e revisione merchant

Le 13 coppie del manifest sono una previsione esplicita della PR originale, **non un'approvazione commerciale**. Il job `merchant-review` fallisce finché non sono presenti revisore nominato e prove indipendenti per ogni coppia, su due host merchant distinti, con variante e quantità. Cambiare soltanto `status` non basta. Non esistono skip per etichette o bypass dei check.

Nello snapshot del 13 novembre erano emersi due join aggiuntivi non previsti, perché le sorgenti Isola erano nuove rispetto al 12 novembre:

| Sorgente | Controparte | Prodotto |
|---|---|---|
| isola-dei-tesori:000120162 | bauzaar:56962032435525 | Piccoli Amici Pellet Conigli Nani Adulti 2,5 kg |
| isola-dei-tesori:000120164 | bauzaar:56962032140613 | Piccoli Amici Pellet Gourmet Conigli Nani Adulti 800 g |

La coincidenza delle firme è una prova interna, non verifica indipendente del prodotto selezionato. Il manifest resta di 13 coppie e il gate deve respingere delta ulteriori finché non siano revisionati e documentati. Gli snapshot successivi sono sempre ricalcolati: il gate salva il delta effettivo, senza fingere che rimanga 15. Nessuna modifica del resolver basata su ID e nessuna estensione automatica del manifest.

## Esecuzione

- `python -m unittest discover -s tests`
- `python automation/check_d1_activation.py --prepare-build` prepara soltanto la fixture locale negata per default.
- `node --test tests/test_*.mjs tests/amazon_*.test.cjs`
- `python tests/check_matching_snapshot_contract.py --base-ref origin/main --output matching-contract-result.json`
- `python tests/check_matching_merchant_review.py` deve fallire quando la review è pending.

Il risultato tecnico non chiude P0 né autorizza merge/deploy. Anche se il delta non coincide, il controllo esegue le verifiche indipendenti successive e salva le differenze e i risultati. La PR rimane bloccata quando manca una prova commerciale. Il rollback è il revert del solo commit del contratto; il merge locale di aggiornamento main è separato. Questa proposta non modifica logica del resolver o dati commerciali.
