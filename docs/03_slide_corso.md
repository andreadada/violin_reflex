# Spunti dalle slide di Computer Vision

Le slide del corso **CV02–CV06** sono riferimenti didattici per progettare gli esperimenti, **non** risultati sul nostro violino. Pagine indicate = numero di pagina del PDF, non necessariamente il numero stampato sulla slide. I PDF del corso non sono caricati nella repository.

| Slide | Contenuto effettivo | Possibile impiego nel progetto | Limite / cautela |
| --- | --- | --- | --- |
| **CV02, pp. 40–43, 75, 78** | Filtri gaussiani e Difference of Gaussians (DoG); uso di scale diverse | Separare variazioni di illuminazione larghe da anomalie a scala intermedia; provare una piramide di scale | Le macchie ampie richiedono scale maggiori; un DoG risponde anche ai bordi del soggetto |
| **CV02, pp. 53–59 e 86–96** | Gradienti Sobel, Canny, massimi locali e isteresi | Individuare corde, contorni forti e ponticello per **interpretare/penalizzare i falsi positivi** | Non escludere tutti i bordi: anche i riflessi sul contorno vanno trattati |
| **CV03, pp. 2–3, 24** | Istogrammi, sogliatura automatica / Otsu | Studiare soglie **adattate alla distribuzione degli score** invece di una soglia manuale invariabile | Otsu su un istogramma non separa da solo riflessi/ombre in un'immagine complessa |
| **CV04, pp. 25–33** | Morfologia binaria, opening/closing, elementi strutturanti orientati | Ripulire maschere candidate, separare strutture sottili da regioni estese | Dimensione e orientamento del kernel possono eliminare riflessi veri |
| **CV05, pp. 14, 20, 27–30** | Morfologia in livelli di grigio; **Top-hat = immagine − opening**, Bottom-hat = closing − immagine | **Priorità:** ricercare eccessi luminosi locali con Top-hat a più scale, confrontandoli tra acquisizioni | Top-hat segnala anche corde, vernice e bordi chiari; una scala non cattura tutte le dimensioni |
| **CV05, pp. 25, 31–32** | Gradiente morfologico, granulometria e texture | Valutare struttura/scala delle regioni candidate; distinguere dettagli sottili da macchie | Dimensione e struttura non provano la natura speculare del segnale |
| **CV06, pp. 3, 7–9, 26** | Confronto di patch, variazioni di illuminazione, feature e orientamento del gradiente | Confrontare **patch allineate** di Base e donatori, penalizzando differenze strutturali/ombre | Correlazioni e gradienti possono preferire ponticello o rumore: non sostituiscono la verifica fotografica |

### Cosa delle slide NON risolve direttamente il problema

- **Canny/Hough (CV06):** rilevano strutture geometriche; la Hough non è necessaria come rilevatore principale dei riflessi.
- **Top-hat:** è un filtro per componenti luminose alla scala dell'elemento strutturante, **non** un classificatore di riflessione speculare.
- **Sogliatura di Otsu:** utile per scegliere una soglia dai dati, **non** per garantire la correttezza semantica della maschera.
- **Filtri per accentuare i dettagli:** aumentare il microcontrasto può anche accentuare rumore, corde e ombre, come visto nel Test 05B.

## Ipotesi concreta per Test 05C — ancora da eseguire

1. Calcolare, per Base e donatori **registrati**, una risposta Top-hat e/o DoG **multi-scala** a partire da luminanza, prima e dopo una compensazione locale prudente.
2. Affiancare una mappa di **gradienti/contorni forti** per valutare dove la risposta è dominata da corde, hardware o sagoma. Non costruire una maschera rigida che elimina automaticamente ogni bordo.
3. Cercare **anomalia di Base rispetto alle singole illuminazioni**, non solo luminosità alta in una foto: distinguere chiaramente una possibile ombra da un riflesso.
4. Produrre diagnostiche a scala 1:8 con controlli nativi nelle zone: macchia superiore destra, ponticello/corde, bordi, legno sano, tavola colori. I ritagli servono **solo per valutazione**, non diventano regole dell'algoritmo.
5. Misurare **precisione dei candidati verificati visivamente** e quantità di veri riflessi mancati; confrontare qualitativamente con Test 05 e 05B. Evitare percentuali di 'riflessi riconosciuti' senza annotazioni affidabili.

**Decisione attuale:** Test 02 è ancora la migliore versione fotografica. Non è stato eseguito Test 05C e nessuna tecnica citata è stata dimostrata migliore sul dataset. La valutazione su altri oggetti è necessaria per affermare la generalità.
