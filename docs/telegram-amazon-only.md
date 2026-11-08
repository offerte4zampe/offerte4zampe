# Telegram Amazon-only (preparato, non attivato)

Il publisher `worker/telegram.mjs` usa il Durable Object esistente, lo stesso cron
Cloudflare e le stesse protezioni di deduplicazione. Il nuovo modo di selezione
`TELEGRAM_CONTENT_MODE=amazon_only` esclude completamente feed Bauzaar, Isola,
Paco e gli altri negozi: **non esiste fallback**.

## Vincolo Amazon

Al momento della verifica (8 novembre 2026), Amazon.it non include Telegram
nell'elenco pubblico dei social network ammissibili alla candidatura. Non
considerare automaticamente ammissibile il canale solo perché il sito o
altri social sono registrati. Servono una conferma scritta Amazon che autorizzi
specificamente `https://t.me/sconti4zampe` e l'inserimento del canale nei
placement/siti approvati, dove consentito. In assenza anche di una sola
condizione, il Worker restituisce `amazon_placement_not_approved` **senza inviare
nessun messaggio**, compreso il vecchio messaggio di test.

Impostazioni di produzione in `wrangler.jsonc`:
- `TELEGRAM_CONTENT_MODE=amazon_only` (solo Amazon)
- `AMAZON_TELEGRAM_PLACEMENT_APPROVED=false` (bloccato)
- `AMAZON_TELEGRAM_CHANNEL_REGISTERED=false` (bloccato)

Solo dopo verifica documentata dei requisiti, configurare entrambe a
`true` e aggiungere `AMAZON_ASSOCIATE_TAG` come variabile protetta
di Cloudflare: non inserire mai un tag inventato o una credenziale nel repository.

## Sorgente e formato

`site/data/telegram-amazon.json` è un manifesto editoriale manuale, inizialmente
vuoto. Ogni elemento di `offers` richiede:
- `asin`: 10 caratteri maiuscoli o numeri, verificato manualmente su Amazon.it;
- `title`: testo originale, accurato;
- `note`: commento originale utile, non una promessa di sconto;
- `image`: immagine originale propria in `/assets/telegram-amazon/<nome>.jpg`
  (anche jpeg/png), con diritto d'uso confermato;
- `reviewed_at`: data ISO in UTC degli ultimi sette giorni;
- `rights_confirmed: true` e `editorial_reviewed: true` (da usare solo dopo
  reale verifica editoriale).

Non importare immagini, testi, prezzi, valutazioni o disponibilità di Amazon
con scraping o da feed non autorizzati. Il post contiene solo una breve nota
originale, disclosure Amazon e un link **diretto** alla pagina prodotto su
Amazon.it con tag; non usa link abbreviati o redirect su offerte4zampe.it.
Non crea price tracking, ribassi, avvisi o storico Amazon.

## Comportamento operativo

Massimo un messaggio al giorno dopo le 09:15 Europe/Rome. Saltare prodotti già
inviati nel Durable Object. Se non ci sono prodotti validi, non pubblicare.
Un errore o un esito ambiguo ferma ulteriori pubblicazioni e richiede controllo
manuale; nessun retry cieco. L'endpoint `/api/telegram/status` mostra la
modalità e il gate autorizzativo, senza mostrare token o tag.

Test da eseguire prima di merge/deploy:
`node --test tests/test_telegram.mjs`

**Attenzione:** la PR di coordinamento #71 tocca anch'essa `worker/telegram.mjs`.
Integrare i cambiamenti in modo esplicito e ripetere i test prima del merge.
