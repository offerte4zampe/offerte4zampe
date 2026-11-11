# Offerte4Zampe

Sito gratuito italiano per proprietari di cani e gatti: calcolo budget, costo cibo, simulatore matematico non assicurativo, checklist e notizie esterne.

## Deploy Cloudflare Pages

Crea un progetto **Cloudflare Pages** con integrazione GitHub per `offerte4zampe/zampachiara`.

- Branch: `main`
- Framework preset: **None**
- Build command: **vuoto**
- Build output directory: **site**
- Root directory: **repository root**

Dopo il collegamento, ogni commit sul branch principale comporterà un deploy automatico.

## Notizie aggiornate

GitHub Actions `.github/workflows/daily-news.yml` cerca collegamenti RSS una volta al giorno. Le notizie importate sono marcate come non verificate editorialmente e riportano link alle fonti; in caso di errore il sito mantiene i link precedenti.

## Monetizzazione

Bauzaar e Isola dei Tesori risultano approvate da email ufficiali TradeTracker del 19 e 20 ottobre 2026. I link affiliati sono dichiarati. Nessuna commissione è certificata senza un report del network; assenza di prova non significa zero vendite. AdSense resta disabilitato. Il catalogo importa prezzi reali dei negozi; il calcolatore giornaliero usa la razione inserita dall’utente. I prezzi possono variare dopo il rilevamento. Il simulatore delle polizze non è un confronto commerciale personalizzato e non svolge distribuzione assicurativa.

## Privacy

Il sito usa un Worker Cloudflare e statistiche facoltative. L'informativa pubblica identifica Mirco Drighetto come titolare e capobranco@offerte4zampe.it come contatto. GA4 563119175 restituisce eventi; i clic non provano vendite. La verifica completa di consenso, conservazione e condizioni dei fornitori resta distinta dalla verifica tecnica.

Contatto: offerte4zampe@gmail.com.

## Separazione dei progetti

Questo repository è indipendente da ExtraVoce e Smart Coaching Engine.

## Catalogo prodotti automatico

`automation/update_catalog.py` importa i cataloghi JSON pubblici di Bauzaar, WebPet e Animaliapet con controllo robots.txt, paginazione e validazione dei prezzi. Il workflow `catalog.yml` aggiorna il catalogo ogni 6 ore. In caso di errore conserva i dati precedenti per quel negozio, segnala la fonte non aggiornata e non inventa prezzi. Le offerte includono variante, disponibilità e data di rilevamento. Il prezzo/kg usa esclusivamente pesi espliciti nei formati, non il peso di spedizione. Spedizione esclusa.

Il confronto non raggruppa per somiglianza del nome: equivalenza automatica solo con GTIN e formato identici. Se il catalogo pubblico non fornisce un GTIN, l'utente può confrontare le offerte selezionate ma deve verificarne l'equivalenza. Gli stati dei singoli programmi e le commissioni vanno verificati nei rispettivi pannelli.

Verifica: `python -m unittest discover -s tests`, `node --check site/assets/catalog.js`.

## Banner e sponsorizzazioni

`site/assets/advertising.js` gestisce banner diretti in home, catalogo, guide e notizie. La configurazione è in `site/data/advertising.json`: nessuna campagna pagata è attiva. In assenza di campagna viene mostrato un invito alla pagina `pubblicita.html`. Il modulo non carica script di reti pubblicitarie, non crea cookie e non traccia impression/clic.

Una campagna diretta richiede `active: true`, `title`, `text`, `url` HTTPS, `placements` (tra `home-between-sections`, `catalog-above-results`, `guides-footer`, `news-footer`), `startsAt` e `endsAt` ISO 8601. Opzionali: `image`, `imageAlt`, `cta`. Ogni banner è etichettato Pubblicità · sponsor e ha link rel=sponsored. Nessun inserzionista inventato o ranking a pagamento.

Per attivare un circuito display (ad esempio AdSense) mancano un account/site approvato, i codici reali delle unità e la configurazione del consenso richiesta dal circuito. Non pubblicare ID dimostrativi né righe ads.txt inventate.
