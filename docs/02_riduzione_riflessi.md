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
| 05B | `2_reflection_step5b.py` | Bilanciamento + microcontrasto; **valutato**, falsi positivi su ponticello e corde |
| 05C | `2_reflection_step5c.py` | Top-hat/DoG multi-scala; **valutato su TIFF reali**, candidati troppo estesi, falso positivo sulla tavola colori |

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

## Test 05B — risultati reali (diagnostica, non fusione)
Input: Base, R1–R4 registrati; mappe a **688 × 1032** (scala 1:8). Lo script `2_reflection_step5b.py` riutilizza `2_reflection_step5.py`.

- **38.530 pixel candidati**, pari al **5,43%** del fotogramma in preview (soglia score 0,090).
- Donatori scelti nei candidati R1–R4: **7.535 / 7.886 / 4.761 / 18.348**; R4 prevale nel **47,6%** delle selezioni, senza che ciò provi che sia il donatore migliore.
- Mappa di microcontrasto: picchi forti su **corde, tastiera, ponticello, effe e tavola colori**, oltre a zone di legno. La macchia diffusa alta a destra non emerge tra le evidenze principali.

| Ritaglio nativo (centro) | Scatto | Score | Guadagno | Microcontrasto Base → donatore |
| --- | --- | ---: | ---: | ---: |
| (3060, 3772), ponticello | R1 | 0,608 | 1,594 | 0,0105 → 0,0108 |
| (2516, 3772), ponticello/legno | R1 | 0,299 | 1,224 | 0,0087 → 0,0105 |
| (3780, 5468), controllo legno | R3 | 0,022 | 1,810 | 0,0059 → 0,0071 |

**Valutazione visiva:** il candidato 1 ha score alto ma R1 presenta **forte ombra sotto il ponticello**; il microcontrasto migliora appena. Il candidato 2 ha microcontrasto più alto ma presenta **zona violacea/lucida e ombra**, senza miglioramento fotografico convincente. La zona di controllo mostra che più microcontrasto non implica un riflesso correggibile. Le mappe includono ancora falsi positivi su componenti rigide e tavola colori.

**Decisione:** Test 05B è un'analisi utile, **non un rilevatore affidabile** e **non un miglioramento di Test 02**. Non creare una fusione basandosi sulla sola mappa 05B. Gli output sono in `output/02_analisi_riflessi/test_05b/` (tre PNG e `osservazioni.md`); nessun TIFF corretto e nessun dato originale modificato.

## Test 05C — risultati reali (diagnostica, non fusione)

Script: `code/phase2_reflection/2_reflection_step5c.py`, dipende da Test 05 e 05B. Mappe **688 × 1032** (1:8), TIFF originali 5504 × 8256 RGB uint8. Supporto stimato senza Hue: **50,8%** del fotogramma; **include erroneamente anche la tavola colori**.

Metodo: Top-hat con raggi **5/15/40** sulla mappa e DoG con sigma **(3,10)/(10,30)/(25,65)**; differenze Base/donatori bilanciati, penalità morbida per gradienti persistenti, soglia score **0,100**. Lo score **non è** una probabilità di riflesso.

| Indicatore | Test 05B | Test 05C |
| --- | ---: | ---: |
| Pixel candidati preview | 38.530 | **84.857** |
| Percentuale fotogramma | 5,43% | **11,95%** |
| Percentuale R4 fra candidati | 47,6% | **61,2%** |
| Falso positivo principale | Ponticello | **Tavola colori** |

Scelte R1/R2/R3/R4 nel Test 05C: **10.369 / 13.179 / 9.408 / 51.901**. L'aumento dei candidati **non dimostra** più riflessi riconosciuti: manca un riferimento annotato.

| Ritaglio (centro) | Donatore | Score | Guadagno | Microcontrasto Base → donatore | Valutazione visiva |
| --- | --- | ---: | ---: | --- | --- |
| (2492, 7404), tavola colori | R4 | 0,514 | 0,83 | 0,0386 → 0,0241 | **Falso positivo** fuori dal soggetto da migliorare |
| (3444, 2964), zona alta destra | R4 | 0,469 | 1,34 | 0,0115 → 0,0053 | **Candidato interessante:** Base appare più slavata; R4 più arancione. Non dimostrata la superiorità della texture/donatore |
| (3292, 6308), controllo legno | R1 | 0,000 | 1,37 | 0,0071 → 0,0047 | Controllo correttamente non selezionato |

Osservazioni sulle mappe:
- **Top-hat:** attiva anche tessitura, corde, contorni, hardware e tavola colori.
- **DoG:** segnala regioni luminose più estese ma risponde anche ai confini strutturali.
- **Differenza multi-luce:** alcune risposte possono essere ombre e non riflessi.
- **Penalità dei bordi:** intercetta parte dei contorni persistenti, non tutti i falsi positivi. Non eliminarli indiscriminatamente: anche i bordi possono riflettere.
- Il supporto non cromatico è più generale della vecchia maschera arancione, ma **non segmenta correttamente l'oggetto di interesse**: include la tavola colori.

**Decisione:** Test 05C aggiunge strumenti diagnostici utili, ma **non è sufficientemente affidabile per guidare una nuova fusione**. R4 prevalente non è prova di superiorità. Il calo del microcontrasto non prova da solo una perdita di dettagli perché anche il riflesso può generare contrasto: richiede ispezione visuale in corrispondenza geometrica.

Output locale: `output/02_analisi_riflessi/test_05c/`, con quattro PNG e `osservazioni.md`. Nessun TIFF corretto. **Test 02 resta la migliore fotografia**.

## Prossima azione — protocollo di valutazione prima di nuovi filtri

1. Annotare manualmente **poche regioni per sola validazione**, includendo il riflesso diffuso alto a destra, eventuali altri riflessi, bordi, elementi strutturali e legno sano; includere esplicitamente la tavola colori tra i negativi.
2. Per ciascuna regione, confrontare Base e **tutti e quattro** i donatori registrati, prima e dopo bilanciamento, osservando riflessi, ombre, colori e texture a pixel nativi. Non giudicare soltanto da score o microcontrasto.
3. Misurare quali regioni candidate vengono riconosciute e quanti falsi positivi restano. Le annotazioni servono **solo a misurare**, non a creare regole hardcoded del violino.
4. Solo dopo decidere se migliorare il supporto/segmentazione generica, il confronto fotometrico o la selezione dei donatori. Conservare gli esperimenti precedenti.

Riferimenti didattici: [03_slide_corso.md](03_slide_corso.md). Nessuna accuratezza quantitativa dimostrata e **nessun nuovo TIFF migliorato** dai Test 05/05B/05C.

Le percentuali di pixel modificati descrivono l'intervento, **non la quantità di riflesso rimossa**. I TIFF e le anteprime restano sul PC.
