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
| 05C | `2_reflection_step5c.py` | Top-hat/DoG multi-scala e penalità contorni; **test tecnico sintetico OK, da valutare su foto reali** |

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

## Test 05C — script diagnostico preparato e provato su dati sintetici

Lo script `code/phase2_reflection/2_reflection_step5c.py` è disponibile in GitHub. Riusa i metodi dei Test 05/05B, prepara mappe a scala 1:8, controlla il contrasto luminoso a più scale con **Top-hat (raggi 5/15/40 px sulla mappa)** e **DoG (sigma 3–10, 10–30, 25–65)**, confronta le quattro luci dopo il bilanciamento locale e penalizza in modo **morbido** i contorni persistenti. Non usa Hue del legno e non esclude rigidamente i bordi.

**Prova tecnica:** esecuzione completata su TIFF RGB sintetici 960×1440, con cinque output creati e nessun TIFF modificato. Il dataset sintetico ha prodotto 5.665 pixel candidati sulla mappa 120×180 con soglia 0,10, ma **non è una misura di accuratezza**: non abbiamo effettuato una valutazione di ground truth e la percentuale di candidati è elevata. Alzare la soglia riduce i candidati, ma può nascondere riflessi reali.

Output attesi sul dataset reale: `output/02_analisi_riflessi/test_05c/01_risposte_multiscala.png`, `02_confronto_illuminazioni.png`, `03_candidati_e_donatori.png`, `04_confronti_nativi.png` e `osservazioni.md`.

**Non ancora validato sul violino**: verificare macchia alta a destra, bordi, ponticello/corde, legno sano e tavola colori. Test 02 resta la migliore fotografia. Test 05C non applica fusione.

## Ipotesi da verificare sui TIFF reali — Test 05C
Valutare **Top-hat e Difference of Gaussians multi-scala** per le anomalie luminose, separare il contributo dei **contorni strutturali** (Sobel/Canny), e confrontare i donatori *nello stesso punto* dopo bilanciamento d'illuminazione. Non creare maschere fissate sul colore arancione o ROI del violino. Usare ritagli nativi di **macchia diffusa**, **bordi**, **ponticello/corde**, **legno senza riflessi** per verificare veri e falsi positivi, non come vincoli per la soluzione.

I concetti e le pagine del corso sono raccolti in [03_slide_corso.md](03_slide_corso.md). **Test 05C è implementato e tecnicamente eseguito su dati sintetici; non è ancora valutato sui TIFF reali.**

Le percentuali di pixel modificati descrivono l'intervento, **non la quantità di riflesso rimossa**. I TIFF e le anteprime restano sul PC.
