# Checkpoint operativo 2026-11-14
taskId: daily-2026-11-14
Priorità: P0
Stato: BLOCCATO / verifica parziale
Snapshot main: be72f39044b274815b79583803882dc078078152 (catalog bot, 2026-11-14 07:11:28 UTC).
Connessione usata esclusivamente: offerte4zampe.

## Evidenza iniziale e causa/ipotesi
Sites get_site conferma registro appgprj_6af22042f78c8191896b40db9d8587fa attivo.
GET /api/updates sul live URL restituito, con OAI-Sites-Authorization e token restituito da Sites: HTTP 401. Nessun token salvato o stampato. Schema e stato del registro non leggibili; nessuna scrittura tentata. Causa non determinata: autenticazione del registro da ripristinare/verificare.
GET reali da questo ambiente a https://offerte4zampe.it/robots.txt, /sitemap.xml, /prodotti, /codici-sconto: HTTP 403. Non prova un guasto del sito per altri client.

## Test prima/dopo ed esito
Nessuna modifica produttiva, nessun merge/deploy.
Ultimo refresh catalogo workflow 43569578643: success, source SHA c3525fcb181c959d8c70dfbf6325e632bfa0994e; ha prodotto lo snapshot main sopra.
Ultimo workflow coupon 43540849842: success, source d4354f4fac1aa02fbd2860d8fbf4667aefcf2fd2.
Fra gli ultimi 10 run: cataloghi/coupon/news/basket smoke/monitor completati con success; preview fase2 skipped. Questo campione non attesta stabilità di tutti i workflow.
PR99 ancora OPEN, merged=false, head cbedbafc0a79c7cbe99b80c1c494c8c252d00809; garanzie e CI della PR non ancora revisionate indipendentemente.
8 test coupon Python passati sul generatore e fixture correnti; rigenerazione locale: 1 scheda (CIOTOLA30). Nessuna pagina pubblicata.

## Coupon, stesso ciclo
Letti automation/coupons.json, automation/build_coupon_page.py, docs/development/coupons.md.
MP20 ha expires_at 2026-11-13T23:00:00Z e verifica del 10 novembre: non idoneo, già escluso dal generatore dopo 48 ore; nessun rinnovo.
Fonti ufficiali Bauzaar, Isola cane e Paco consultate il 14 novembre; la pagina Bauzaar conserva promozioni indicate al 13 novembre, che non costituiscono proroga.
Browser Paco prodotto 5278 mostra RED3 (-2 EUR sul 2 kg) e RED8 (-8 EUR sul 12 kg). Tentativo selezione 2 kg senza cambiamento osservabile/controllo quantità: prova carrello incompleta, nessun articolo aggiunto, nessun codice applicato. Prezzo pagina variante 2 kg 19,90 EUR; prezzo dopo sconto NON MISURATO. Codici esclusi, nessun verified_at modificato.
Pannelli affiliati e GSC non verificati in questa esecuzione. Nessun acquisto, account, iscrizione, messaggio o invio marketing.

## Impatto, rischio e rollback
Checkpoint solo documentale, produzione invariata. Nessuna attestazione deploy esatto SHA, indicizzazione GSC, integrità completa cataloghi, discrepanze Cat&Rina/Fish4Dogs o 100 matching: tutti NON VERIFICATI e P0 aperto. Nessuna metrica ignota convertita in zero.
Rollback: eliminare/revertire questo documento nel branch, senza effetti sul sito.

## Proposta e prossimo passo
Mirco: ripristinare accesso API del registro (401 con token corrente). Poi leggere stato/schema, importare questo checkpoint senza duplicare taskId e riprendere controlli P0. Verificare HTTP da client autorizzato e attestazione Cloudflare sull'esatto SHA, GSC attuale, anomalie merchant e campione indipendente di almeno 100 matching. Nessuna modifica di produzione finché registro non disponibile, secondo istruzioni.

## Ripresa manuale del programma — 14 novembre

Le evidenze precedenti restano storiche del ciclo mattutino. Nuova lettura GitHub: PR100 head d17ba8271794d6d517c180a57a6378946519e217 ha Basket browser smoke 43508373324 SUCCESS (test Python/JavaScript, generatori, mobile e desktop) e Cloudflare Workers Builds SUCCESS del ramo. Phase2 preview SKIPPED è coerente con il workflow riservato al solo ramo di anteprima spedizioni; non è una deroga a un controllo generale. Nessun merge o deploy di produzione.

Main corrente 75e97818daafde9af7da6aa324360565fb0c6c8a: Cloudflare SUCCESS, build 022ffc87-db0f-4e3e-b4ac-7c3011820dd0, versione del build abd520ef-9021-41d3-860b-51c2c6cdfda5. Smoke indipendente 14 novembre: quattro URL commerciali prioritarie HTTP200, canonical self, noindex assente; 557/557 schede collegate. Catalogo aggiornato 07:08 UTC, 18.040 offerte, sei fonti OK. Non attestato tramite confronto diretto l'ID della versione attiva.

Riallineamento locale PR100 al main corrente: un test usava un ID storico non più presente; fixture in correzione con campionamento deterministico del catalogo corrente, mantenendo le garanzie complete dei redirect. Nuovo SHA e CI da documentare dopo pubblicazione del ramo.

PR99 non aggiornata né integrata: contratto di matching in ricostruzione dal checkpoint persistito. Le letture merchant del ciclo serale precedente non sono presenti nel checkpoint salvato e non vengono dichiarate disponibili; nuova raccolta delle prove per i 15 join candidati (13 iniziali e due nuove offerte) in corso. Nessun ampliamento automatico della allowlist e nessun tasso di precisione certificato.

API registro: in questa ripresa GET riuscita inizialmente; successivi tentativi di scrittura hanno incontrato errori di tunnel/rete 403/000, distinti dal401 del ciclo mattutino. Non dichiarato accesso in scrittura ripristinato; nessuna credenziale o configurazione cambiata. Checkpoint su questo ramo come fallback autorizzato. Il blocco del registro non autorizza a sospendere lavoro indipendente su branch e PR.

### Registro nuovamente accessibile nella verifica indipendente

Nuovo tentativo ordinario con service access appena acquisito: GET, POST e readback tutti HTTP200. Registrato record56, taskId pr100-verification-2026-11-14, stato In attesa. Evidenze CI/main/557collegamenti conservate nel centro. Il blocco precedente non si è riprodotto in questo tentativo; causa non dimostrata, nessuna credenziale/configurazione cambiata. Non è quindi richiesta al proprietario una modifica di accesso sulla sola base del primo errore.
