# Rilettura delle regole di spedizione — 23 novembre 2026

Attività P1: rinnovare la prova delle condizioni di sei merchant dopo rilettura delle fonti ufficiali. Sono rinnovate le date per30giorni; tariffe, soglie, limiti di peso e casi ignoti restano invariati. Il seedSQL è un derivato per staging: non vengono eseguite migrazioni né attivato D1.

| Merchant | Fonti ufficiali rilette | Regola mantenuta |
|---|---|---|
| Bauzaar | https://www.bauzaar.it/pages/tempi-di-evasione |6,90€ sotto59€; gratis oltre59€ entro35kg; soglia esatta, peso mancante/eccessivo e casi speciali ignoti. |
| WebPet | https://www.webpet.it/policies/shipping-policy e https://www.webpet.it/policies/terms-of-service |5,90€ sotto39,90€; gratis oltre; formulazioni discordanti all'esatta soglia, che resta ignota. |
| Animaliapet | https://www.animaliapet.eu/policies/shipping-policy | Policy Express5,99€ indipendentemente dal subtotale, entro30kg di peso verificato. Non applicata la gratuità del banner69€. |
| Isola dei Tesori | https://www.isoladeitesori.it/faq.html |5,90€ sotto59€, gratis oltre;59€ esatti ignoti. |
| Paco | https://www.pacopetshop.it/it/cms/7/spedizione-consegna-paco | Poste domicilio5,90€ sotto79€, gratis oltre;79€ esatti ignoti per discordanza fra testo e riepilogo. |
| Hygge | https://hyggepetfood.com/policies/shipping-policy e https://hyggepetfood.com/pages/faq |7,90€ sotto40€, gratis oltre;40€ esatti ignoti perché policy inclusiva e FAQ/banner esclusivi. |

Metodo: fonti pubbliche ufficiali lette23novembre; nessun accesso a checkout autenticato, ordine o pagamento. I preventivi valgono soltanto per Italia continentale ordinaria, pagamento anticipato e servizi standard descritti nelJSON. Non sono una garanzia del prezzo finale del checkout.

Test: suite quote/soglie/quantità/territori/scadenze e rigenerazione idempotente del seed; confrontare prima/dopo i preventivi con orologio fisso e prezzi invariati. Nessun costo ignoto viene trasformato in zero. Rollback: revert di questa PR; la verifica precedente mantiene la propria scadenza originale.

Il seed è idempotente su un database nuovo o sullo stesso insieme di versioni. Non è una migrazione per un database già popolato col seed precedente: senza chiudere i vecchi intervalli il controllo restituisce correttamente `overlapping shipping rules`. Nessuna applicazione a database esistenti è prevista da questa modifica.
