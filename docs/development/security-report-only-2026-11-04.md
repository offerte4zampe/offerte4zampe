# Diagnostica header delle schede prodotto

La funzione `canonicalProduct` passa tutte le sue risposte attraverso `reportSecurityHeaders`: HTML200, HEAD,400,404,405 e redirect301. Il wrapper copia la risposta e conserva body, status, Location, Allow, cache e ogni header già presente, comprese eventuali policy più restrittive. Non modifica le preferenze di tracciamento e non esegue richieste ai negozi.

`worker/security-headers.mjs` contiene come riferimento gli stessi cinque nomi/valori di `site/_headers`. Un test verifica che il riferimento resti allineato al file corrente. La diagnosi controlla soltanto la presenza dei nomi: non certifica la correttezza o equivalenza dei valori già impostati. Quando mancano header, il log server contiene esclusivamente `event: security_headers_report_only` e `missing_headers`, un array di nomi fissi della policy. Non registra URL, query, cookie, IP, prezzi, identità o valori degli header. Un errore del logger non interrompe la risposta.

L'unica aggiunta HTTP è `X-O4Z-Security-Mode: report-only`. È un indicatore applicativo non standard, privo di effetto sulle protezioni del browser. Non esistono modalità report-only native per HSTS o X-Frame-Options: aggiungere questi header normali applicherebbe subito una policy. Questa modifica pertanto non li aggiunge, non introduce CSP, non rimuove o indebolisce policy esistenti e non simula un enforcement. Non configura Reporting-Endpoints e non raccoglie report client.

I log permettono di contare le risposte con header mancanti tramite l'evento e i nomi ammessi. Le richieste ripetute generano eventi ripetuti; il conteggio descrive risposte osservate, non utenti unici. Copertura: soltanto risposte del gestore canonico; gli altri percorsi Worker non sono implicitamente coperti.

L'eventuale enforcement richiederà una decisione successiva dell'utente, dopo revisione dei log, verifica dei valori e controlli di compatibilità. Non è incluso né attivabile mediante parametro di query o variabile introdotta qui.

## Link per saltare al contenuto

Le schede inseriscono `<base href="/">` per risolvere gli asset. Un link relativo `#main` altrimenti punta alla home. Il rendering sostituisce questo href con il percorso della scheda corrente, mantenendo la query e aggiungendo `#main`. Il valore è escaped per HTML. Il canonical SEO resta senza query. Sono coperti il percorso base e il ricalcolo con quantity/territory.

## Verifica locale

- `python automation/check_d1_activation.py --prepare-build`: build JSON; D1 e shadow bloccati in assenza di attestazione.
- `node --test tests/test_security_headers.mjs tests/test_canonical_product.mjs tests/test_canonical_redirects.mjs`:19/19 passati.
- `node --test tests/test_*.mjs`:175/175 passati,0falliti (34,2s).
- `git diff --check`:superato.
- Test della diagnostica: policy allineata, assenza di nuove restrizioni, preservazione valori esistenti, redirect immutabili, Allow/cache/body e gestione errore logger.
- Test del gestore reale: status200/400/404/405/301, HEAD, canonical/query, risoluzione skip link con basehref e log privi di dati di richiesta.

Nessun commit, push o deploy eseguito da questa attività.
