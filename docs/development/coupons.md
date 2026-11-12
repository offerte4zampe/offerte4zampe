# Codici sconto — 29 ottobre 2026

Solo codici provati nel carrello: fonte ufficiale, prova positiva su prodotto/variante specifici, condizioni e scadenza esplicite. publication_allowed indica l'autorizzazione editoriale alla pubblicazione di un codice pubblico, non remunerazione del network. Link diretti alle selezioni ufficiali, nessun tracking affiliato inventato.

## Prove reali
FC20: Forcepet Cat Adult Sterilised Digestive Soft patè 85 gr, Orata, 1 confezione: 1,50 → 1,20 €, sconto 0,30 €, codice visibile nel carrello.
LILY20: Snack Treats 70 gr Chicken Bites, 1 confezione: 3,48 → 2,79 €, riduzione osservata 0,69 € (arrotondamento del negozio). Carrello misto con Forcepet da 1,50 €, rimasto escluso da LILY20: totale 4,29 €.
Nessun acquisto. La prova non garantisce ogni variante né cumulabilità. Articoli di prova rimossi.

Fonte https://www.bauzaar.it/pages/promozioni: 20% sulle rispettive marche, senza minimo dichiarato, non cumulabile, scorte limitate, scadenza 31/10.
Non pubblicati ISOLA50 (futuro e non testato), FREE (richiede account primo ordine idoneo), Paco (ancora da testare).

## Mantenimento
verified_at usa conservativamente l'inizio UTC del giorno di prova; non è un'ora esatta inventata.
Visibilità limitata al minore fra scadenza, recheck_after e 48h dalla prova. Errori, dati incompleti, prove future o senza riduzione: esclusione. Il generatore non rinnova mai una prova.
Nuove verifiche richiedono browser e lettura del carrello, nessuna simulazione tramite chiamate HTTP nascoste. Il checkout del negozio resta il riferimento finale.
Rigenerazione ogni sei ore con workflow coupons.yml, controllo data anche nel browser ogni minuto. Automazione quotidiana al mattino Europe/Rome: controlla fonti e carrello, aggiorna solo dopo prova, esclude blocchi. Nessuna sottoscrizione, messaggio, acquisto o invio marketing.

5 test Python mirati locali passati; CI mobile e deploy da registrare a pubblicazione conclusa.

## 6 novembre 2026
MP20 (Bauzaar): prova nel carrello su due confezioni di biscotti Monopro Dog Adult All Breeds Grain Free 100 g, Tacchino, variante 56819967164741. Riga da 6,00 € a 4,80 €, sconto visibile 1,20 €. Articoli e codice rimossi a fine prova. Fonte: https://www.bauzaar.it/pages/promozioni — Monopro −20%, senza minimo, non cumulabile, fino al 13 novembre e a esaurimento scorte. Nuovo controllo entro il limite di 48 ore dalla data registrata.


## 7 novembre 2026 — audit fonti, sospensioni e policy

- **FC20 e LILY20**: marcati `expired` e `publication_allowed: false`; la scadenza ufficiale registrata era il 31/10/2026. Nessun rinnovo della prova.
- **MP20**: unica prova positiva recente ancora valida. Il sito Bauzaar continua a mostrare MP20 al -20% su Monopro fino al 13/11, senza spesa minima, non cumulabile e con scorte limitate. La prova del 06/11 (2 × biscotti Monopro Tacchino 100 g, variante 56819967164741: 6,00 € → 4,80 €) resta invariata; `verified_at` non è stato rinnovato. `recheck_after` resta 08/11/2026 00:00 UTC.
- **CIOTOLA30 (Hygge)**: non provato nel carrello, quindi sospeso dalla pubblicazione. Rimossa l'eccezione `partner_provided`: il generatore pubblica esclusivamente righe `cart_tested` con prova positiva e limite massimo di 48 ore. I test Python e browser sono stati allineati a questa regola.
- **Nuovi candidati Bauzaar, non pubblicati**: STY20 (-20% Stuzzy) e PP20 (-20% Purina Pro Plan), entrambi indicati fino al 13/11, senza minimo, non cumulabili e con scorte limitate; RELAX (-25% cucce, non cumulabile, senza scadenza espressa); BZR20 (-20% sul primo ordine dei brand esclusivi, richiede login/registrazione e non è cumulabile). Tutti attendono prova reale nel carrello.
- **Conflitto Bauzaar**: per Fish4Dogs la descrizione e il pulsante indicano FD20, mentre il riquadro copiabile mostra FC20. Registrato come `source_conflict`, escluso fino a chiarimento e prova.
- **Paco**: la pagina ufficiale elenca SCORTA3 (3% da 150 €), SCORTA4 (4% da 200 €), SCORTA5 (5% da 250 €), non cumulabili e senza scadenza indicata. La pagina prodotto The Red Oak indica RED3 (-2 € sul formato 2 kg) e RED8 (-8 € sul formato 12 kg). Tutti registrati come candidati non verificati. WPACO5 (-5% primo ordine) è escluso perché l'uso comporta l'iscrizione alla newsletter, vietata dalle istruzioni di questo controllo.
- **Isola dei Tesori**: le pagine pubbliche di promozione cane/gatto mostrano sconti sui prodotti ma non espongono un codice coupon testuale; nessun codice nuovo inserito.
- Nessun nuovo test nel carrello: in questa esecuzione non era disponibile una sessione browser interattiva autorizzata per i negozi. Non sono stati creati account, effettuate iscrizioni, completati acquisti o inviati messaggi. Nessun `verified_at` è stato modificato.
- Fonti ufficiali consultate: Bauzaar https://www.bauzaar.it/pages/promozioni ; Isola https://www.isoladeitesori.it/promozioni/promozioni-cane/ e https://www.isoladeitesori.it/promozioni/promozioni-gatto/ ; Paco https://www.pacopetshop.it/it/cms/3/codici-sconto-e-promozioni-di-paco e https://www.pacopetshop.it/it/the-red-oak/5278-the-red-oak-maiale-e-mele-grain-free-per-cani.htm .

## 8 novembre 2026 — prova reale MP20

Browser Bauzaar: Monopro lo specialista Dog Adult All Breeds Biscotti Grain Free 100 gr, Tacchino, variante 56819967164741, 1 confezione. Prezzo prima 3,00 EUR; dopo inserimento MP20 2,40 EUR; riduzione visibile 0,60 EUR con MP20 sulla riga. Nessun acquisto; codice rimosso e carrello confermato vuoto. Fonte promozioni: Monopro -20%, senza minimo, fino al 13/11. Osservato inoltre WE65 (-6 EUR da 69 EUR, indicato fino alle 23:59), non testato e non pubblicato. Conflitto FD20/FC20 ancora presente. Questa registrazione non rinnova verified_at: pubblicazione, rigenerazione, test e verifica deploy ancora da completare. Nessuna verifica odierna dei pannelli affiliati, Isola o Paco.

## 10 novembre 2026 — rinnovo MP20

Prova reale nel browser: Monopro biscotti Dog Adult All Breeds Grain Free 100 g, Tacchino, variante 56819967164741, 1 confezione; 3,00 → 2,40 EUR, MP20 visibile sulla riga e sconto 0,60 EUR. Codice e articolo rimossi; carrello vuoto confermato. Nessun acquisto. Fonte ufficiale Bauzaar conferma -20%, senza minimo, non cumulabile, scorte limitate, scadenza 13/11. verified_at conservativo 10/11 00:00 UTC; esclusione dal 12/11 00:00 UTC. Link esistenti e CIOTOLA30 conservati. Otto test coupon passati e pagina rigenerata con 2 schede. Fixture storica dei test isolata dal rinnovo dei dati reali. Fonti pubbliche Paco e Isola consultate; candidati senza nuova prova restano esclusi. Pannelli affiliati non verificati. CI e deploy ancora da confermare.

## 12 novembre 2026 — scadenza della verifica MP20

MP20 escluso automaticamente dal 12/11 00:00 UTC per raggiungimento delle 48 ore; controllo HTTP pubblico conferma assenza della scheda MP20 e presenza di CIOTOLA30. Nessun rinnovo di verified_at e nessuna nuova prova nel carrello effettuata. Fonte Bauzaar continua a dichiarare la promozione fino al 13/11: questo non rinnova l'evidenza. Otto test coupon superati; rigenerazione locale include solo CIOTOLA30. Nessuna modifica alla pagina necessaria: esclusione già online. Fonti pubbliche Isola e Paco consultate; rilettura dettagli Paco bloccata da HTTP 403. Pannelli affiliati non verificati e candidati non testati ancora esclusi. Nessun acquisto, account, newsletter o messaggio.
