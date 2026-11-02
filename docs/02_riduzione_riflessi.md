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

**Esito visivo: primo miglioramento parziale.** Il confronto mostra un'attenuazione visibile della macchia principale, soprattutto nella zona superiore destra, mantenendo un aspetto complessivamente naturale. Rimangono riflessi vicino alle effe e sui bordi. La mappa d'intervento indica dove sono cambiati i pixel, non dimostra una separazione fisica dei riflessi.

**Limite del metodo:** il punteggio premia cromaticità e luminosità, ma non verifica che un donatore conservi davvero venature più leggibili. Aumentare indiscriminatamente l'intensità rischia di scurire il legno o creare aloni. **Test 02 da conservare come prima candidata promettente, non come risultato finale.**

## Test 03 — Verifica delle aree da migliorare

**Script locale:** `2_reflection_step3.py`  
**Output:** `output/02_analisi_riflessi/test_03/`

Confronti a pixel nativi tra Base, Test 02 e i quattro donatori (anche normalizzati). Nessun TIFF modificato.

| Area analizzata | Delta luminosità medio Base−Test 02 |
| --- | ---: |
| Zona migliorata, parte superiore destra | +21,52/255 |
| «Riflesso residuo» (ponticello) | +2,46/255 |
| «Bordo» (cordiera) | +0,05/255 |
| Legno sano di controllo | +0,00/255 |

**Osservazione:** la riduzione luminosa nella prima area è consistente con l'attenuazione visibile del riflesso. Ma il selettore automatico ha individuato ponticello e cordiera al posto di altri riflessi sul legno. Non usare queste scelte come maschere di correzione.

## Test 04 — Fusione protetta (da verificare)

**Script locale:** `2_reflection_step4.py`, preparato e testato tecnicamente su immagini sintetiche; **non eseguito sul dataset reale**.

Riutilizza pesi e guadagni del Test 02. Aggiunge una maschera cromatica del legno, con verifica dei pixel alla risoluzione nativa; incrementa moderatamente la forza nei soli punti già candidati. Intende evitare interventi su corde, ponticello e cordiera. Non garantisce di correggere i riflessi totalmente bianchi o azzurri sui bordi.

**Output previsto:** `output/02_analisi_riflessi/test_04/`, con TIFF fullres, confronto Base/Test 02/Test 04, mappa, maschera e report. Valutare al 100% macchia principale, bordi, effe e zone sane prima di trarre conclusioni.

## Vincoli

Nessuna sovrascrittura dei TIFF o degli output validati. Codice e immagini restano nel progetto locale; GitHub contiene soltanto documentazione.
