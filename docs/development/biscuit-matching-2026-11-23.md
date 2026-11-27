# Due confronti O-life verificati — 23 novembre2026

La sola equivalenza lessicale `biscottini → biscotti` recupera due coppie esatte: O-life Dog Adult200g Agnello/ortica/semi di lino e200g Tacchino/mela/curcuma. Le varianti Bauzaar56819870925125 e56819870826821 sono state lette nel payload ufficiale selezionato; le schede Isola000134207 e000134209 confermano ciascuna ricetta, marca, linea, destinazione e confezione. Le prove indipendenti con date, hash e fingerprint dell’offerta sono nel manifesto dei test. Non vengono copiati o inventati GTIN mancanti nel feed. Il metodo resta dichiarato per nome e caratteristiche.

Replay sul medesimo snapshot23Nov07:33UTC:18.254 offerte, confronti561→563, prodotti canonici attivi16.698→16.696. Tutti15 join precedentemente revisionati e i2 hold restano invariati. Prezzi, disponibilità, URL affiliati e quantità restano quelli delle fonti. La ricetta alternativa, età, confezione, altri brand e formati non verificati sono controesempi bloccanti.

Escluso il candidato Hill’s14kg: le fonti non dimostrano la stessa versione/formulazione. Non sono aggiunti alias `breeds`, `canine` o `feline`. La somiglianza testuale o fotografica non basta. Non si deduce la fattibilità del10% da queste due coppie.

Aggiornamento27 novembre: snapshot08:24UTC con18.340 offerte, prodotti attivi16.787→16.785 e confronti574→576 (3,42→3,43%). Sono presenti12 delle15 coppie storiche; tre ID mancano già sulla baseline: Isola000122044, Isola000120161, Bauzaar56962032435525. Non è dimostrata la causa upstream e non si ripristinano offerte vecchie. Il registro schema3 conserva integralmente le prove delle tre coppie dormienti, data/snapshot/commit/digest e assenze esatte; verifica ancora il fingerprint del membro presente. Ricomparsa cambiata o prova scaduta falliscono; la coppia tornata identica passa nuovamente il gate completo prima di rientrare nel contratto. Questo registro è una garanzia di test, non una nuova hold di produzione.

Verifiche obbligatorie prima del rilascio: gate stretto delle14 coppie presenti (12 storiche+2 nuove), archivio esplicito delle3 assenti, contratto completo su snapshot, test negativi e CI. Rollback: revert della PR e rigenerazione del catalogo, senza modificare le offerte merchant.


Rivalidazione sul catalogo27 novembre21:19UTC (commit7363678):18.336 offerte,589→591 confronti,16.749→16.747 prodotti attivi,3,52→3,53%. Gate14+3, due soli ID mossi, ogni altro gruppo e ogni campo commerciale invariati,12 confronti storici/3 assenze/2 hold invariati. Date delle prove originali conservate. Questi numeri restano una simulazione fino alla generazione e verifica pubblica post-merge.

Rivalidazione finale dopo il collector Paco, input2e5cfbf e snapshot27 novembre21:25:43UTC:18.336 offerte,591→593 confronti,16.747→16.745 prodotti attivi,3,53→3,54%. Gate14+3 e confronto stretto confermano i medesimi due soli ID mossi; tutti gli altri gruppi,12 storici,3 assenze e2 hold invariati. Nessuna data fonte rinnovata.
