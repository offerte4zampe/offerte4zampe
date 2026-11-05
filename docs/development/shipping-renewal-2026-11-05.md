# Rinnovo circoscritto del 5 novembre 2026

La provenienza delle tariffe è costituita dalle pagine ufficiali sotto riportate,
non da una scheda o conferma fattuale dell'utente. L'utente ha approvato il perimetro
operativo conservativo: quattro negozi, sole fasce non ambigue, 30 giorni di validità.
Rilettura documentale iniziata il 2026-11-05T10:31:55.515Z (11:31:55 CET).
Le letture delle pagine non costituiscono simulazioni di carrello.

| Negozio | Fonte ufficiale (senza utm_source) | Evidenza e perimetro applicato |
| --- | --- | --- |
| Bauzaar | https://www.bauzaar.it/pages/tempi-di-evasione | 6,90 sotto 59; gratis oltre 59 solo con peso di spedizione noto, fino a 35 kg. A 59 ignoto. Peso mancante o oltre 35: ignoto, senza stimare supplementi. |
| Isola | https://www.isoladeitesori.it/faq.html | 5,90 sotto 59; gratis oltre 59. A 59 ignoto. Isola Plus non applicato alla consegna standard ordinaria. |
| Paco | https://www.pacopetshop.it/it/cms/7/spedizione-consegna-paco | «Sotto i 79 euro la consegna costa 5,90 euro.» Solo domicilio con Poste; gratis oltre 79. A 79 ignoto. Punto Poste e Fermopoint BRT esclusi. |
| WebPet | https://www.webpet.it/policies/shipping-policy | 5,90 sotto 39,90; gratis oltre 39,90. A 39,90 ignoto per conservare il confine dubbio. |
| WebPet, controllo incrociato | https://www.webpet.it/policies/terms-of-service | Apertura diretta inizialmente non accessibile; lettura riuscita seguendo il link dal footer ufficiale nella medesima sessione. Conferma 5,90 sotto 39,90; non viene usata come prova della gratuità al confine. |
| Hygge, non rinnovato | https://hyggepetfood.com/policies/shipping-policy | Riletto nella sessione; non equivale alla rilettura del checkout precedente. Nessuna nuova simulazione di checkout dichiarata; nessuna regola aggiunta. |

Animaliapet conserva la precedente osservazione scaduta e conflittuale. Hygge resta
senza regola. Nessun dato ricavato da snippet di ricerca viene usato per le tariffe.
Le quattro osservazioni rinnovate scadono il 2026-12-05T10:31:55.515Z
(11:31:55 CET), esattamente 30 giorni dopo. Avviso dal 21 novembre alla stessa ora.
Il monitor resta warning-only per default, non scrive regole e non crea issue.

## Esclusioni e uso

Il totale automatico riguarda esclusivamente Italia continentale ordinaria,
domicilio e pagamento anticipato. Isole, CAP disagiati, Livigno, Campione,
contrassegno, appuntamento e punti di ritiro richiedono la selezione della
destinazione/servizio particolare e restituiscono ignoto. Non si deduce il CAP.
Non si modifica alcun URL affiliato o preferenza di consenso.

Il seed SQL è rigenerato solo per mantenere verificabili conversione ed equivalenza
in staging locale: non viene eseguita alcuna migrazione o attivazione D1 remota.

## Anteprima remota

Il nome nel file wrangler.phase2-preview.jsonc è ancora `zampachiara`, uguale alla
produzione: non soddisfa la condizione richiesta del nome Worker distinto.
Nessun upload, rerun remoto o push sul ramo PR che possa avviare quel workflow.
I controlli remoti di tre prodotti per negozio restano non eseguiti/non simulati.
Le precedenti simulazioni parziali non vengono presentate come verifiche di questa patch.

## Risultati effettivi

- Python: 248 test superati.
- Node: 220 test superati, nessuno saltato; inclusa matrice di 610 casi JSON/righe e roundtrip SQLite, zero differenze.
- Build Cloudflare Wrangler 4.154.0 dry-run: riuscita, ASSETS e variabili JSON soltanto; nessun upload.
- Workerd locale: fallito all'avvio con `uv_interface_addresses returned Unknown system error 1`; nessuna matrice workerd dichiarata superata in questa esecuzione.
- Anteprima remota: non eseguita per il nome Worker non distinto. Nessun URL remoto creato.
- Tre prodotti per ognuno dei quattro negozi sull'anteprima remota: non eseguiti; confronto checkout non simulato.
- Prime esecuzioni Node: un errore nel test di peso (default del helper ripristinava il peso omesso), un prerequisito generato D1 assente e un test con concatenazione di data incompatibile con timestamp ISO. Corretti helper/prerequisito/test; suite finale 220/220.

I file generati dalla build sono stati ripristinati per mantenere il commit circoscritto.
Il monitor non è stato modificato: default warning-only e nessuna API di apertura issue;
il nuovo test copre avviso a 14 giorni e uscita zero dopo la scadenza.
