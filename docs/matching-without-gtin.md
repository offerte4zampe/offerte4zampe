# Matching senza GTIN

Le identità restano fondate su GTIN valido e quantità di vendita verificata, oppure su uguaglianza completa delle caratteristiche normalizzate. Le parole commerciali generiche (mangime, alimento, cibo, crocchette) e traduzioni lessicali esplicite non impediscono la corrispondenza. Marca, linea, ricetta, età, variante, dimensioni e confezione rimangono significative. Quantità secondarie discordanti e GTIN validi in conflitto bloccano il collegamento. Nessun GTIN viene inventato o copiato nell’offerta mancante.

Descrizioni e immagini alimentano esclusivamente la coda di revisione. I testi già presenti nelle risposte dei feed e Shopify vengono trasformati in impronte SHA256, con fonte e data: non si ripubblica la descrizione. Una descrizione di prodotto può essere condivisa tra varianti e non certifica quella selezionata. I confronti richiedono prove recenti riferite alla stessa offerta.

Le foto vengono confrontate solo se già nella cache autorizzata, individuata dall’URL originale dell’offerta. L’immagine condivisa dalla pagina canonica non viene riutilizzata come prova, evitando ragionamenti circolari. Nessun download aggiuntivo e nessuna estensione dei permessi delle immagini. Foto uguali o simili possono appartenere a gusti, taglie o confezioni differenti.

La coda considera esclusivamente offerte disponibili e aggiornate, di negozi diversi, con marca e quantità verificate compatibili. Esclude prodotti già collegati e coppie entrambe dotate di GTIN valido. Ricette, età, indicazioni veterinarie, specie, profumi, taglie e dimensioni incompatibili vengono scartati. La somiglianza dei nomi è un ordinamento, non una probabilità di identità. Il confronto immagini è limitato alle prime 500 coppie per somiglianza del titolo; una coppia esclusa da questo limite può quindi non apparire anche con foto simili. La revisione richiede ancora conferma indipendente della variante e della confezione.

## Verifica sul catalogo

Snapshot: 2026-11-12T21:11:08.174328+00:00. Base: 417e922b8e9efdb9f9e2db061519ac0fc115c6e3. Esecuzione a data fissa, stesso catalogo, confronto tra resolver originale e modificato.

| Misura | Prima | Dopo |
|---|---:|---:|
| Prodotti attivi | 16.345 | 16.332 |
| Prodotti confrontabili tra negozi | 562 | 574 |
| Copertura | 3,44% | 3,51% |
| Offerte attive non collegate | 7.116 | 7.103 |

Tredici gruppi acquisiscono offerte: dodici diventano confrontabili e uno amplia un confronto esistente. Le coppie per revisione sono 334 e non sono collegamenti approvati. Dettagli e ID sono in `matching-audit-2026-11-12.json`. Prezzo, URL, link affiliato, disponibilità, GTIN, peso e stato di verifica della quantità sono stati confrontati per ID offerta e risultano invariati.

Lo snapshot non contiene descrizioni: il guadagno misurato deriva dalle regole testuali esatte. Le nuove impronte si popoleranno attraverso le normali acquisizioni già previste. Le quantità non verificate, soprattutto per Paco, restano escluse: foto o descrizioni generiche non le rendono certe.

Validazione locale: 315 test Python e 269 test JavaScript; casi positivi e negativi per ricetta, età, veterinario, profumo, taglia, dimensioni, quantità sconosciuta, GTIN discordanti, descrizioni scadute e immagini senza permessi. I risultati sono una simulazione; questa modifica non pubblica da sola un nuovo catalogo in produzione.
