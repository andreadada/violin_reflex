# 03 — Analisi RAW

**Stato: esplorativa.**

## Obiettivo

Verificare se lo sviluppo uniforme dei file NEF e il confronto tra le singole illuminazioni permettano di stimare meglio la componente indesiderata.

## Prove

I cinque NEF sono stati sviluppati con `rawpy` adottando una procedura comune: demosaicizzazione AHD, bilanciamento del bianco della fotocamera, sRGB a 16 bit, senza auto-brightness né denoise.

È stata anche verificata l'ipotesi di additività delle illuminazioni: ricostruire Base dai quattro scatti con una luce accesa ciascuno.

## Osservazioni

- Lo sviluppo RAW comune produce una resa sensibilmente più scura dei TIFF originali: sulla zona di legno analizzata, mediana **58,5** contro **93,3** per Base TIFF, sulla scala diagnostica 0–255.
- La decomposizione additiva semplice ha restituito componenti negative in circa **40–62%** dei pixel nelle prove considerate: l'ipotesi non è sostenuta dai dati.
- Una verifica dell'allineamento ha mostrato un impatto limitato sul problema di additività (circa **0,29 punti percentuali**).

## Conclusione

Non è stata identificata una ricetta di sviluppo RAW calibrata che recuperi direttamente la superficie senza riflessi. Non usare la semplice sottrazione delle immagini come soluzione validata.

Le possibili cause della non additività (illuminazione variabile, acquisizione, pipeline fotografica) non sono state isolate sperimentalmente.
