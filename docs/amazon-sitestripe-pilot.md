# Selezione iniziale Amazon / SiteStripe

Selezionati il 12 novembre 2026 dal catalogo operativo aggiornato alle 2026-11-12T19:02:10.781021+00:00. Criteri: almeno due negozi verificati, diversità di marche e specie. Non è una classifica per traffico o domanda.

| Prodotto | Formato | Scheda |
|---|---|---|
| Almo Nature HFC Natural Dog Adult Filetto di Pollo 95 g | 95 g | [Apri](https://offerte4zampe.it/prodotto/almo-nature-hfc-natural-filetto-di-pollo-95g-lattina-cani-adulti-08001154120769-fee615) |
| Camon VegTwist Snack Dentali Vegetali 400 g | 400 g | [Apri](https://offerte4zampe.it/prodotto/camon-vegtwist-snack-vegetali-per-cani-confezione-da-400-gr-08019808199597-5e69e3) |
| Monge Supreme Sterilised Tonno con Calamari Lattina 80g Gatti | 80 g | [Apri](https://offerte4zampe.it/prodotto/monge-supreme-sterilised-tonno-con-calamari-lattina-80g-gatti-08009470007894-0c2572) |
| Monge Kitten Monoprotein Trota 1,5Kg Gattini | 1,5 kg | [Apri](https://offerte4zampe.it/prodotto/monge-kitten-monoprotein-trota-1-5kg-gattini-08009470005500-1c9c68) |
| Nature's Protection White Dogs Pesce Bianco Small e Mini Adult 1,5kg Crocchette Cani | 1,5 kg | [Apri](https://offerte4zampe.it/prodotto/nature-s-protection-white-dogs-pesce-bianco-small-e-mini-adult-1-5kg-crocchette-cani-04771317456670-a6d199) |
| Royal Canin Cat Kitten Jelly 85 g | 85 g | [Apri](https://offerte4zampe.it/prodotto/royal-canin-kitten-in-jelly-85g-bustina-gattini-09003579311714-28eac6) |
| Royal Canin Cat Adult Sterilised in Salsa 85gr | 85 g | [Apri](https://offerte4zampe.it/prodotto/royal-canin-sterilised-in-salsa-bustine-85g-gatti-09003579311301-daf673) |
| Cat's Best Original lettiera 7lt / 3Kg | 3 kg | [Apri](https://offerte4zampe.it/prodotto/cat-s-best-original-lettiera-7lt-3kg-04002973213353-8530b0) |
| Monge Gemon All Breeds Adult con Maiale e Riso 3 kg | 3 kg | [Apri](https://offerte4zampe.it/prodotto/monge-gemon-maiale-e-riso-3kg-crocchette-cani-all-breeds-adult-08009470386012-438ed4) |
| Monge Natural Superpremium Crocchette per cani adulti con Maiale, riso e patate 12 kg | 12 kg | [Apri](https://offerte4zampe.it/prodotto/monge-all-breeds-adult-monoprotein-con-maiale-riso-e-patate-per-cani-sacco-da-12-kg-tutte-le-taglie-08009470011112-f968d2) |
| Monge Monoprotein Coniglio 1.5Kg Crocchette Gatti | 1,5 kg | [Apri](https://offerte4zampe.it/prodotto/monge-monoprotein-coniglio-1-5kg-crocchette-gatti-08009470011945-57c2af) |
| Royal Canin Kitten in Salsa 85 g | 85 g | [Apri](https://offerte4zampe.it/prodotto/royal-canin-kitten-in-salsa-85g-bustina-gattini-09003579308943-e38ec8) |

## Passaggio necessario prima dell'attivazione

Per ciascuna scheda verificare su Amazon.it marca, linea, ricetta, taglia, peso e numero di confezioni; acquisire il link SiteStripe con tracking ID offerte4zam0c-21. Nessun ASIN o URL è stato inventato. Le righe in automation/amazon-sitestripe-selection.json sono solo una coda editoriale: non vengono lette dal Worker e non attivano pulsanti.

Il registro esistente contiene quattro prodotti (sette associazioni a offerte): Beaphar No Stress gatto 35 cm e KONG Classic S, L, XL. Le verifiche registrate risalgono al 21 ottobre 2026 e scadono dopo 30 giorni; non sono state rinnovate senza nuove evidenze.

## Comportamento dell'interfaccia

Il riquadro Amazon appare subito dopo il confronto prezzi e prima dello storico. Prezzi e disponibilità si consultano su Amazon; esclusione da classifica, dati strutturati delle offerte, storico e avvisi. Dichiarazione affiliati accanto al pulsante. AMAZON_LINKS_ENABLED resta false e PRICE_TRACKING_ENABLED resta false. Nessuna modifica alle regole degli altri negozi.

## Verifica e rilascio

Test locali: node --test tests/test_amazon_links.mjs tests/test_amazon_ssr.mjs. Per il solo import locale del renderer è necessaria l'attestazione generata worker/generated/d1-validation.json, con remote_success false quando non esiste attestazione remota. Non commettere quel file. Prima di qualsiasi attivazione completare i link, verificare le associazioni sul catalogo corrente ed eseguire CI e smoke dell'anteprima. Non è stato eseguito un deploy.
