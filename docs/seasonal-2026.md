# Vestiti stagionali — Offerte a 4 Zampe (2026–2027)

La decorazione si attiva **solo nel browser** sulla base del calendario `Europe/Rome`, in tutte le pagine che caricano `site/assets/base.js`. Il catalogo, il confronto fra negozi, i prezzi e le dichiarazioni di sconto rimangono invariati.

| Tema | Attivo automaticamente | Palette e messaggio |
| --- | --- | --- |
| Black Week | 23–30 novembre 2026 inclusi | Antracite, oro, accento crema; confronto e sconti **solo** verificati |
| Natale a 4 Zampe | 1 dicembre 2026 – 6 gennaio 2027 inclusi | Verde pino, crema, oro; idee regalo e prezzi da confrontare |

Il Black Friday 2026 cade il **27 novembre** e il Cyber Monday il **30 novembre**. Il sito torna al tema standard il 7 gennaio 2027.

## Anteprime già disponibili appena il codice viene distribuito

- Black Week: `https://offerte4zampe.it/?previewTheme=blackfriday`
- Natale: `https://offerte4zampe.it/?previewTheme=natale`
- Tema normale: `https://offerte4zampe.it/?previewTheme=off`

La preview vale soltanto per la pagina aperta: nessun cookie, nessun salvataggio delle preferenze. Il link non dichiara che le promozioni siano già iniziate, perché mostra `ANTEPRIMA`.

## Garanzie

- Non alterare prezzo precedente, percentuale, disponibilità o catalogo.
- Non affermare che le offerte commerciali siano reali senza le verifiche già previste.
- Non inserire timer falsi o urgenze artificiali.
- Rispettare `prefers-reduced-motion` e rendere i link accessibili da mobile.
- Il CSS stagionale viene caricato solo quando il tema è attivo.
- Ogni anno occorre definire nuove date, evitando una campagna vecchia attiva all'infinito.

Verifica automatica: `node --test tests/test_seasonal_theme.mjs tests/test_seasonal_2026.mjs`.
