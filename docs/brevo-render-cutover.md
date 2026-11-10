# Newsletter Brevo: migrazione a uscita stabile

## Configurazione pronta

Servizio **separato** `offerte4zampe-newsletter`, cron Render Starter a Francoforte,
repository `offerte4zampe/offerte4zampe`, branch `main`, Python 3.12.
Build: `python3 -m unittest discover -s tests -p 'test_*newsletter*.py' -v`.
Comando: `python3 -m automation.run_render_newsletter`.
Orario: lunedì 08:15 UTC (09:15 Italia in inverno, 10:15 in estate).
Il job termina entro quattro minuti. Nessuna modifica ai servizi Smart Coach.

Render applica un minimo di **1 USD/mese per cron**; il consumo è a tempo.
Non creare il servizio prima dell'approvazione del costo ricorrente.

Gli IP regionali sono un insieme stabile **condiviso**, non un singolo IP dedicato.
Leggere i CIDR effettivi da **Connect > Outbound** del nuovo servizio e ottenere
l'approvazione specifica prima di aggiungerli all'allowlist Brevo.
Non copiare intervalli di altre regioni o autorizzare tutti gli IP GitHub.
Gli IP dedicati Render richiedono Pro e hanno un costo aggiuntivo: non necessari
per questa configurazione, salvo scelta esplicita del proprietario.

## Attivazione controllata

1. Creare il servizio con `BREVO_SEND_ENABLED=false` e le altre variabili di
   `render.brevo.yaml`. Conservare la chiave Brevo solo nelle variabili segrete
   Render, inserita dal proprietario; mai nel repository, nei log o in chat.
2. Verificare build e run manuale in dry run. Devono passare gli stessi controlli
   su catalogo entro 12 ore, data odierna, almeno tre offerte valide, immagini,
   formato, mittente e lista del sender esistente.
3. Approvare e autorizzare in Brevo i soli CIDR restituiti dal servizio. Mantenere
   il blocco IP API attivo. L'allowlist condivisa è un filtro aggiuntivo: la chiave
   API rimane necessaria per ogni chiamata.
4. Impostare la variabile repository GitHub `BREVO_SEND_RUNTIME=render` e
   verificare che nessun vecchio invio GitHub sia ancora in esecuzione.
   GitHub continua a preparare articolo e social, ma salta la chiamata Brevo.
5. Solo dopo il cutover, impostare su Render `BREVO_SEND_ENABLED=true` e avviare
   un run manuale. Verificare ID campagna e stato in Brevo; un run verde da solo
   non prova la consegna alle caselle. Il nome giornaliero previene i reinvii.
6. Registrare servizio, CIDR approvati, run, ID campagna e risultato nella regia.

## Recupero e rollback

Se l'invio viene bloccato, lasciare il job disabilitato e ispezionare i log.
Non disattivare il controllo IP e non autorizzare automaticamente IP nuovi.
In caso di campagna già creata ma invio incerto, verificarne lo stato in Brevo:
il sender rifiuta di ricrearla automaticamente, anche nei rerun.
Per rollback: prima disabilitare l'invio Render; solo dopo, rimuovere la variabile
repository `BREVO_SEND_RUNTIME` per riabilitare GitHub. GitHub continuerà a essere
soggetto al proprio problema di IP variabile finché l'allowlist è attiva.

Fonti: https://render.com/docs/cronjobs e
https://render.com/docs/outbound-ip-addresses (verificate 10 novembre 2026).
