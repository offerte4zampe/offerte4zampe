# Varianti Shopify mancanti: sospensione con doppia prova

Un feed può continuare a pubblicare una variante che il prodotto del negozio non contiene più. Il link con quel parametro può rispondere 200 scegliendo un altro colore o formato. Questo non è un redirect HTTP e non va trattato come prova del prezzo della variante richiesta.

## Criterio conservativo

La sola assenza nell’API `.js` resta inconcludente. Il nuovo controllo richiede congiuntamente:

- URL diretto già autorizzato per Bauzaar, WebPet o Animaliapet; parametro variante uguale all’ID dell’offerta;
- API HTTP200 del prodotto esatto, ID numerico, handle uguale al percorso, elenco non vuoto di ID unici e meno di250 varianti;
- assenza dell’ID richiesto da quell’elenco;
- seconda risposta HTTP200 all’URL di vendita esatto, senza seguire redirect e dopo verifica robots;
- canonical autocorrispondente al prodotto; blocco `MainProduct` con stesso ID prodotto e percorso;
- oggetti JSON selezionati nei picker della stessa sezione principale, tutti concordi e corrispondenti a un’altra variante contenuta nell’API. Titolo, SKU, barcode, prezzo e disponibilità selezionati devono coincidere con quell’oggetto API. Quick view e prodotti correlati non forniscono la prova.

La [documentazione ufficiale Shopify](https://shopify.dev/docs/api/ajax/reference/product) limita l’elenco dell’API a250 varianti. Al limite il controllo non presume che l’elenco sia completo. Risposte bloccate, errori, HTML non riconosciuto, selezioni ambigue e strutture incomplete restano inconcludenti.

## Applicazione e limiti

Il collector effettua al massimo una seconda GET per ognuna delle offerte già scelte dal budget esistente. Non visita Amazon, redirect affiliati o carrelli. Nessun ID è codificato nella logica di produzione.

Il record conserva URL API e documento, status, impronte SHA256, ID prodotto, ID assente e selezioni osservate. La sospensione richiede inoltre fonte API prevista, impronta della riga originale e prova non futura entro24ore. La forma della prova viene rivalidata prima dell’applicazione. Cambiare soltanto uno stato o il prezzo nel catalogo non consente di riutilizzare una prova riferita a un’altra osservazione.

La riga viene esclusa dal catalogo pubblicato, conservando nel report originale e prova. Prezzo, stock, URL e identificativi non vengono riscritti; non si seleziona la variante alternativa. La successiva importazione ricostruisce le righe. Un record scaduto, cambiato o inconcludente non le sospende. L’HTML non viene conservato nella prova pubblicata, solo fatti e hash.

I temi non riconosciuti non sono automaticamente coperti. La doppia prova documenta lo stato osservato del prodotto: non certifica inventari fisici o transazioni. Eventuali aggiornamenti del negozio richiedono nuove osservazioni.

## Verifica e rollback

Test negativi coprono cap API, elenco vuoto/duplicato, prodotto o URL diverso, variante nuovamente presente, HTML mancante o ambiguo, raccomandazioni, errori/reindirizzamenti e robots, cache scaduta/futura e riga cambiata. I test conservano originale e link affiliato senza promuovere la variante alternativa.

Rollback: revert dei soli file della modifica e dell’eventuale nuova voce di prova, poi normale rigenerazione verificata dopo autorizzazione al rilascio. Non alterare raw feed, segreti o flag Amazon. Una PR e test verdi non autorizzano merge o deploy.
