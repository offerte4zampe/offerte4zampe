# Preview nativa isolata per la fase 2

`wrangler.phase2-preview.jsonc` riusa entrypoint, asset e comando di build del sito, con JSON come fonte di spedizione e shadow disabilitato. Non contiene route di produzione, cron, Durable Objects, migrazioni, Analytics Engine, D1, KV, R2, servizi, segreti, keep_vars o ambienti ereditati. `workers_dev` è false e `routes` è vuoto. Il nome di riferimento nella configurazione è `zampachiara`; ogni comando del workflow lo sovrascrive con `phase2-<numero PR>`.

La pubblicazione usa esclusivamente la preview nativa di Wrangler4.154.0:

```sh
wrangler preview --config wrangler.phase2-preview.jsonc --ignore-base-config --name "$PREVIEW_NAME" --json
```

Questa configurazione non collega risorse di produzione e non esegue un deploy permanente, caricamento di versioni sul Worker di produzione, aggiornamento di route/DNS o migrazioni. Non rende disponibili Telegram, invii newsletter o dataset di tracking mediante binding: l'assenza è intenzionale. La preview resta un caricamento remoto di codice/asset nell'account Cloudflare; la configurazione dei permessi del token resta responsabilità dell'ambiente `cloudflare-staging`.

Il workflow `.github/workflows/phase2-isolated-preview.yml` accetta soltanto eventi PR opened/synchronize/reopened con repository sorgente identico al repository base e branch esatto `phase2/shipping-metadata-preview-20261104`. Checkout sullo SHA della PR, senza credenziali Git persistenti. Nessun trigger manuale e nessun `pull_request_target`. I permessi GitHub sono contents:read.

Prima dell'upload:

1. Installa Python3.12, Node22, Pillow12.3.0 e Wrangler4.154.0.
2. Prepara la build JSON, mantenendo D1/shadow bloccati senza attestazione.
3. Compila localmente con `wrangler deploy --dry-run` e configurazione isolata; questo comando non carica codice o asset.
4. Esegue le suite complete Python e Node, inclusi i controlli d'isolamento.

Solo lo step `Upload native preview only` riceve le due credenziali già usate dall'ambiente staging: `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID`. Non riceve token affiliati, credenziali Telegram, Brevo o altri segreti applicativi. L'upload viene eseguito solo se tutti gli step precedenti hanno successo. Il risultato JSON e i log di build/test sono conservati come artifact per7giorni anche in caso di errore. I log non devono stampare credenziali.

Il comando preview non è stato eseguito durante la preparazione di questi file. Nessun upload, deploy o modifica remota è stato eseguito dall'agente. Il controllo browser e l'estrazione dell'URL preview saranno integrati dal coordinatore dopo l'upload; la sola presenza dell'URL non dimostra il superamento dei controlli.

## Test locale della configurazione

`node --test tests/test_phase2_preview_config.mjs`:3/3 superati. Verifica whitelist delle chiavi, assenza di binding/route, uguaglianza della build e degli asset, restrizione della PR, pin della CLI, posizione dei segreti e ordine dei controlli prima della preview. YAML analizzato localmente senza errori. La dry-run completa della configurazione sarà eseguita dal coordinatore; la CLI remota non è stata invocata in questa attività.

## Acceptance checks added to this branch

`tests/check_phase2_preview.mjs` accepts only localhost or a `phase2-*` workers.dev origin. It checks the real Worker response, report-only marker, expired-rule explanation, declared liter price, GET recalculation on the preview origin, lazy history, optional statistics opt-in/opt-out and the six merchants' redirect Location values. Affiliate destinations are compared byte-for-byte with the snapshot and are never followed by the HTTP checks. For the browser click, the original `_blank` target and sponsored relations are first asserted; that one test anchor is temporarily kept in the intercepted tab so the external destination can be blocked before navigation. This verifies the actual `/go/` redirect without contacting a merchant/network. It does not claim checkout validation or test popup behavior end to end.

The URL parser rejects production, other preview names, credentials, query tokens, fragments and ambiguous URLs. Secrets are available only during the native preview upload step, never during test execution. No production deployment command is included.
