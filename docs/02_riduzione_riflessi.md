# 02 — Riduzione fotografica dei riflessi

**Obiettivo:** migliorare esteticamente l'intero violino, bordi inclusi, senza separare fisicamente luce diffusa e speculare. Base è il riferimento fotografico; le altre quattro immagini sono già registrate.

## Test 01 — Confronto delle illuminazioni

**Script locale:** `2_reflection_step1.py`  
**Output:** `output/02_analisi_riflessi/test_01/`

Panoramica affiancata delle cinque fotografie, senza modificarle. Base ha l'illuminazione più equilibrata; i singoli scatti presentano zone diversamente illuminate e riflessi in posizioni differenti. Nessuno sostituisce da solo Base. Il confronto a dimensione ridotta non basta a giudicare la trama del legno.

## Test 02 — Fusione selettiva

**Script locale:** `2_reflection_step2.py`  
**Output:** `output/02_analisi_riflessi/test_02/`

Una maschera cromatica delimita il violino; a scala 1:8 vengono scelti donatori tramite saturazione, luminanza, esposizione e coerenza della tonalità. La fusione è applicata sul TIFF a risoluzione nativa, mantenendo Base come riferimento.

| Misura | Risultato |
| --- | ---: |
| Immagine | 5504 × 8256 px, RGB uint8 |
| Pixel modificati ≥ 1 livello | 4.872.007 (10,72% del fotogramma) |
| Area eleggibile stimata | 33,81% dell'anteprima |
| Alpha medio nelle zone candidate | 0,148 |

**Esito visivo: insufficiente.** Il prima/dopo è quasi identico. Persistono riflessi evidenti vicino alle effe, nella zona alta a destra e sui bordi. La mappa d'intervento segnala soprattutto differenze d'illuminazione: non certifica la rimozione di riflessi.

**Limite del metodo:** il punteggio premia cromaticità e luminosità, ma non verifica che un donatore conservi davvero venature più leggibili. Aumentare l'intensità rischia di scurire il legno o creare aloni. Test 02 non approvato come risultato finale.

## Prossimo esperimento — Test 03

**`2_reflection_step3.py` — Verifica della qualità dei donatori.**

- Analizzare l'intera superficie, **anche il bordo**, partendo dalle cinque immagini registrate e dalle maschere di validità.
- Confrontare aree omologhe a **pixel nativi**, includendo zone lucide e zone sane di controllo. Separare esposizione generale da visibilità della texture.
- Produrre una tavola di confronti e una mappa dei candidati **senza creare ancora una nuova fusione**.
- Verificare visivamente se almeno una fotografia mostra dettagli autentici meglio leggibili dove Base ha il riflesso.

**Criterio di decisione:** se l'informazione utile esiste, progettare una correzione globale ma selettiva; altrimenti cambiare approccio, non intensificare il blend.

## Vincoli

Nessuna sovrascrittura dei TIFF o degli output validati. Codice e immagini restano nel progetto locale; GitHub contiene soltanto documentazione.
