# 02 — Riduzione fotografica dei riflessi

**Goal:** attenuare i riflessi in immagini multi-scatto con illuminazioni diverse, preservando un aspetto naturale. Il violino è un caso di prova; evitare soluzioni dipendenti dalle sue caratteristiche. Vedi [obiettivo](00_obiettivo.md).

Gli script sono in `code/phase2_reflection/` e sono eseguibili dalla root del progetto. I TIFF e gli output locali restano nelle cartelle originali.

| Test | Script | Risultato |
| --- | --- | --- |
| 01 | `2_reflection_step1.py` | Confronto delle cinque illuminazioni; nessuna correzione |
| 02 | `2_reflection_step2.py` | Fusione selettiva; **migliore risultato attuale** |
| 03 | `2_reflection_step3.py` | Analisi nativa dei donatori e di Test 02; nessuna nuova correzione |
| 04 | `2_reflection_step4.py` | Maschera del legno più selettiva; **non preferito** a Test 02 |
| 05 | `2_reflection_step5.py` | Diagnostica multi-luce, ampia corrispondenza ma molti falsi positivi |
| 05B | `2_reflection_step5b.py` | Bilanciamento luminoso + microcontrasto; **da valutare sui TIFF reali** |

## Test 02 — baseline
Fusione basata su normalizzazione lenta dei donatori, cromaticità, luminosità ed esposizione, mantenendo Base come riferimento.

- **4.872.007 pixel** modificati ≥1 livello: **10,72%** del fotogramma.
- Alpha medio nelle zone candidate: **0,148**.
- **Riduzione visibile** del riflesso principale sulla parte alta destra; resa complessivamente naturale.
- Altri riflessi (incluse zone del bordo) restano. Anche Test 02 contiene **euristiche legate al dataset**: non è una soluzione generale validata.

Output locale: `output/02_analisi_riflessi/test_02/01_correzione_globale.tif`.

## Test 03 — cosa abbiamo verificato
Confronto a pixel nativi tra Base, Test 02 e i quattro donatori (anche normalizzati).

| Area | Differenza media Base−Test 02 |
| --- | ---: |
| Macchia migliorata | +21,52/255 |
| «Riflesso residuo» — in realtà ponticello | +2,46/255 |
| «Bordo» — in realtà cordiera | +0,05/255 |
| Legno sano | +0,00/255 |

La selezione automatica delle aree è stata **in parte errata**. La riduzione di luminanza è coerente con l'attenuazione visibile della macchia, ma non dimostra una separazione fisica dei riflessi.

## Test 04 — risultato reale
Maschera cromatica specifica del legno, con alpha Test 02 × **1,35** (limite **0,72**) e limiti al delta RGB.

- Pixel modificati rispetto a Base: **5.583.326 (12,29%)**.
- Diversi dal Test 02: **5.035.582 (11,08%)**.
- Nella comparazione Base/Test 02/Test 04, **Test 02 è preferito visivamente**: sembra più pulito e naturale.
- La maschera basata sul legno arancione **non generalizza** su colori/materiali diversi; può escludere i riflessi bianchi/azzurri.

**Decisione:** conservare Test 02 come baseline. Test 04 rimane un esperimento utile ma non una revisione approvata.

## Test 05 — risultati reali
Mappa di eccessi luminosi locali e confronto tra Base e i singoli scatti a scala 1:8. **58.949 su 61.523 candidati Base (95,8%)** hanno almeno un candidato nelle singole illuminazioni entro cinque pixel di anteprima. Non è sensibilità/accuratezza del rilevatore: molte aree non sono riflessi (corde, contorni, tavola colori). La somma luminosa approssimata ha dato **R² holdout 0,5626** e non costituisce una ricostruzione fisicamente calibrata di Base.

## Test 05B — diagnostica preparata
Lo script `2_reflection_step5b.py` (usa funzioni di `2_reflection_step5.py`) confronta i quattro scatti dopo bilanciamento fotografico lento, calcola indizi da eccesso di luminosità di Base, microcontrasto e rischio d'ombra. Produce in `test_05b/` tre immagini e `osservazioni.md`. Nessun TIFF corretto. **Provato su TIFF sintetici, non ancora valutato sulle fotografie reali.**

**Decisione sospesa:** conservare Test 02 come baseline, controllare i ritagli nativi e i falsi positivi prima di progettare la fusione successiva.

Le percentuali indicano pixel modificati, **non la quantità di riflesso rimossa**. Tutti i TIFF e le anteprime restano in `output/02_analisi_riflessi/` sul PC.
