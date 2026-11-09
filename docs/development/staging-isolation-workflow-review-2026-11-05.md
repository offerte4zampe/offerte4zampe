# Staging isolato e audit workflow — 5 novembre 2026

Commit precedente preservato: `fe241089164f7db8db8a2a008d69de5cbe72eb9a`.

## Diff Wrangler

```diff
-  "name": "zampachiara",
+  "name": "zampachiara-staging",
```

Solo `wrangler.phase2-preview.jsonc` cambia. `wrangler.jsonc` di produzione è invariato.
Staging: routes vuote, nessun custom_domain, workers_dev false; unico binding ASSETS locale;
solo variabili SHIPPING_RULES_SOURCE=json e SHIPPING_SHADOW=false. Nessun KV/R2/D1,
Durable Object, Analytics Engine, service binding, cron, keep_vars o dichiarazione di segreti.
I due segreti GitHub di cloudflare-staging sono credenziali di upload, non binding Worker.
La presenza e lo scope effettivi dei segreti non sono stati ispezionati in questo commit;
la configurazione riferita dall’utente non è una lettura dei valori.

## Eventi e rami (snapshot del ramo da proporre alla PR #56)

| Workflow | Eventi e filtri di ramo | Guardia job |
| --- | --- | --- |
| agent-readonly-tests.yml | pull_request base=qualsiasi; paths=2 filtri (vedere YAML); workflow_dispatch | test: nessuna |
| basket-browser.yml | workflow_dispatch; pull_request branches=main; push branches=main; paths=112 filtri (vedere YAML) | mobile: nessuna |
| catalog.yml | schedule default branch; push branches=main; paths=82 filtri (vedere YAML); workflow_dispatch | refresh: github.ref == 'refs/heads/main' && github.event_name != 'pull_request' |
| cloudflare-mcp-capabilities.yml | workflow_dispatch | discover: nessuna |
| cloudflare-mcp-check.yml | workflow_dispatch | verify: nessuna |
| cloudflare-worker-monitor.yml | workflow_dispatch; push branches=main; paths=2 filtri (vedere YAML); schedule default branch | audit: nessuna |
| coupons.yml | schedule default branch; workflow_dispatch; push branches=main; paths=7 filtri (vedere YAML) | refresh: github.ref == 'refs/heads/main' && github.event_name != 'pull_request' |
| d1-activation.yml | pull_request branches=main; paths=7 filtri (vedere YAML); push branches=main; paths=7 filtri (vedere YAML) | verify-remote-evidence: nessuna |
| d1-staging.yml | pull_request branches=main; paths=10 filtri (vedere YAML); workflow_dispatch | local-workerd: nessuna; remote-staging: github.event_name == 'workflow_dispatch' && inputs.remote; remote-status: always() |
| daily-news.yml | schedule default branch; workflow_dispatch | update-news: github.ref == 'refs/heads/main' && github.event_name != 'pull_request' |
| home-merchandising-tests.yml | pull_request base=qualsiasi; paths=5 filtri (vedere YAML); push branches=main; paths=5 filtri (vedere YAML) | validate: nessuna |
| hygge-validation.yml | push branches=feature/hygge-awin-feed; workflow_dispatch | test: nessuna |
| phase2-isolated-preview.yml | pull_request base=qualsiasi types=opened,synchronize,reopened,labeled | preview: github.event.pull_request.head.repo.full_name == github.repository && github.event.pull_request.head.ref == 'phase2/shipping-metadata-preview-20261104' && (github.event.action != 'labeled' \|\| github.event.label.name == 'phase2-preview-approved') |
| seasonal-2026-tests.yml | pull_request base=qualsiasi; paths=6 filtri (vedere YAML); push branches=main; paths=6 filtri (vedere YAML) | validate: nessuna |
| shared-layout.yml | pull_request base=qualsiasi; paths=19 filtri (vedere YAML) | regression: nessuna |
| shipping-rules-monitor.yml | schedule default branch; workflow_dispatch | observe: nessuna |
| site-audit.yml | workflow_dispatch; push branches=main; paths=1 filtri (vedere YAML) | lighthouse: nessuna |
| telegram-ci.yml | push branches=main; paths=4 filtri (vedere YAML); pull_request base=qualsiasi; paths=4 filtri (vedere YAML); workflow_dispatch | telegram: nessuna |
| telegram-regression.yml | push branches=main; paths=3 filtri (vedere YAML); workflow_dispatch | test: nessuna |
| verify-home-live.yml | push branches=main; paths=8 filtri (vedere YAML); workflow_dispatch | verify: nessuna |
| weekly-brevo-newsletter.yml | schedule default branch; workflow_dispatch | send: github.ref == 'refs/heads/main' && github.event_name != 'pull_request' |

## Controlli di pubblicazione

- Nessun `wrangler deploy` effettivo di produzione nei workflow ispezionati: le chiamate deploy sono dry-run.
- catalog, coupons, daily-news e weekly-brevo-newsletter hanno ora una guardia `github.ref == refs/heads/main` ed esclusione pull_request; il dispatch da questo ramo non può scrivere contenuti su main o inviare newsletter.
- Preview: eventi PR opened/synchronize/reopened eseguono build e test senza upload.
- Upload esclusivamente su un nuovo evento labeled con etichetta `phase2-preview-approved`, da applicare solo dopo approvazione esplicita. La semplice presenza preesistente dell’etichetta non abilita upload ai successivi synchronize.
- La preview è limitata alla PR della stessa repository con head phase2/shipping-metadata-preview-20261104; checkout dello SHA esatto, permessi contents:read.
- Matrice workerd locale aggiunta prima di ogni upload nel workflow preview. Il workflow d1-staging offre inoltre un job locale automatico su PR verso main con i paths rilevanti. Il job remoto D1 resta separato, solo workflow_dispatch con remote=true: non richiesto e non verrà eseguito.
- Nessun push, modifica PR, esecuzione Actions o upload effettuato durante questa preparazione.
- Non è verificata qui l’eventuale integrazione Cloudflare Git esterna ai workflow: prima del push verificare che il ramo non abbia un auto-deploy configurato fuori da GitHub Actions. La scansione YAML da sola non dimostra la configurazione del pannello Cloudflare.

## Verifiche locali

5 test Node di configurazione e 3 test Python di validazione URL passati.
Nessuna nuova esecuzione workerd locale dichiarata riuscita: il precedente errore di rete resta aperto.
I 248 Python/220 Node e build dry-run del rinnovo sono risultati del commit precedente, non di una nuova esecuzione su Actions.

## Scadenza

Le quattro regole scadono il 5 dicembre 2026 alle 11:31:55.515 CET; avviso a 14 giorni dal 21 novembre alla stessa ora.
Dopo la scadenza i totali tornano ignoti; il monitor warning-only non rinnova le regole e non blocca gli import.
La schedule sul ramo non è attiva: GitHub esegue le schedule sul default branch. Prima del merge servono controlli manuali per osservare queste versioni delle regole.
