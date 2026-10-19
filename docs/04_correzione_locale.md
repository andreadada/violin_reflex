# 04 — Correzione locale

**Stato: prototipo, non validato.**

## Approccio

Su una regione selezionata (ROI), il prototipo confronta Base con uno dei quattro scatti registrati e produce una proposta con transizione graduale (*feather*).

Sono stati provati due metodi:

1. **RGB compensata:** trasferimento di informazione cromatica dal donatore con compensazione locale.
2. **Solo luminanza, dettaglio Base:** modifica prevalentemente la luminanza a bassa frequenza, conservando i dettagli ad alta frequenza di Base.

Parametri principali: donatore, intensità della correzione, larghezza del feather.

## Prove osservate

| Prova | Intensità | Feather | Osservazione |
| --- | ---: | ---: | --- |
| Riflesso 4, solo luminanza | 35% | 80 px | Variazione debole; la macchia resta |
| Riflesso 4, solo luminanza | 100% | 25 px | Forte scurimento locale, senza eliminazione convincente della macchia |

Nel secondo caso il cambiamento medio di luminanza osservato è stato di circa **−32,93 livelli** sulla scala 8 bit. Un'ulteriore prova RGB ha comportato alterazioni più marcate del colore e dei dettagli.

## Limite principale

Attenuare la luminosità dell'intera ROI non equivale a separare il riflesso dalla superficie. Una metrica di dettaglio stabile (es. Laplaciano) non dimostra da sola che la venatura sia stata preservata correttamente.

## Decisione

Non affinare ulteriormente slider e interfaccia finché non è verificato se **almeno un donatore** mostri la macchia attenuata mantenendo informazione reale sul legno. Nessuna delle proposte locali è una soluzione finale approvata.
