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

## Revisione delle descrizioni fornite dal proprietario

Confermati n.4 Monge Kitten Trota 1×1,5 kg, n.6 Royal Canin Kitten Jelly 1×85 g, n.9 Gemon Adult Maiale Riso 1×3 kg, n.10 Monge Adult Maiale Riso Patate 1×12 kg, n.11 Monge Adult Coniglio 1×1,5 kg. Registrate 13 associazioni esatte alle offerte del catalogo, tutte con URL SiteStripe originale conservato.

Esclusi dalle schede originarie: n.1 12×280 g anziché 95 g; n.3 24×80 g anziché 80 g; n.7 Kitten Sterilised 4×12×85 g anziché Adult Sterilised 85 g. N.5: confermati pesce bianco e 1,5 kg dal proprietario, ma Small/Mini White Dogs non esplicito; resta sospeso. N.2/8 non disponibili, n.12 duplicato segnalato dal proprietario.

I redirect dei nove link forniti risolvono verso Amazon.it con tag offerte4zam0c-21; le pagine finali restituivano HTTP 503. Le conferme delle varianti derivano dalle descrizioni del proprietario, non da un'ispezione riuscita delle pagine Amazon.

## Passaggio necessario prima dell'attivazione

Per le varianti ancora sospese completare la verifica di marca, linea, ricetta, taglia, peso e numero di confezioni. Nessun ASIN o URL è stato inventato. La selezione in automation/amazon-sitestripe-selection.json conserva gli esiti della revisione; il Worker usa esclusivamente site/data/amazon-links.json. Le cinque varianti confermate sono nel registro, ma AMAZON_LINKS_ENABLED resta false.

Il registro esistente contiene quattro prodotti (sette associazioni a offerte): Beaphar No Stress gatto 35 cm e KONG Classic S, L, XL. Le verifiche registrate risalgono al 21 ottobre 2026 e scadono dopo 30 giorni; non sono state rinnovate senza nuove evidenze.

## Comportamento dell'interfaccia

Il riquadro Amazon appare subito dopo il confronto prezzi e prima dello storico. Prezzi e disponibilità si consultano su Amazon; esclusione da classifica, dati strutturati delle offerte, storico e avvisi. Dichiarazione affiliati accanto al pulsante. AMAZON_LINKS_ENABLED resta false e PRICE_TRACKING_ENABLED resta false. Nessuna modifica alle regole degli altri negozi.

## Verifica e rilascio

Test locali: node --test tests/test_amazon_links.mjs tests/test_amazon_ssr.mjs. Per il solo import locale del renderer è necessaria l'attestazione generata worker/generated/d1-validation.json, con remote_success false quando non esiste attestazione remota. Non commettere quel file. Prima di qualsiasi attivazione completare i link, verificare le associazioni sul catalogo corrente ed eseguire CI e smoke dell'anteprima. Non è stato eseguito un deploy.

Aggiornamento verifiche: 10/10 test locali superati, inclusi conservazione byte per byte dei link originali, rifiuto di host contraffatti, tracking diverso, ASIN diverso, conferma assente, confezioni discordanti e associazioni scadute. Suite completa e smoke mobile non ancora eseguiti. Nessun merge o deploy.
