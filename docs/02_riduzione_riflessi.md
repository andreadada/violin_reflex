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

## Prossimo esperimento — Test 03

**`2_reflection_step3.py` — Analisi e miglioramento della fusione del Test 02.**

- Prendere il Test 02 come punto di partenza: capire perché attenua la macchia principale.
- Confrontare a **pixel nativi** i donatori nelle zone ancora lucide, **bordi inclusi**, e nelle zone sane di controllo.
- Verificare dove sono effettivamente visibili dettagli utili, distinguendoli da semplici differenze di esposizione.
- Solo dopo la verifica, modificare selettivamente il metodo per estendere il miglioramento senza scurire la superficie.

**Criterio di decisione:** mantenere il miglioramento già ottenuto e aumentare la qualità fotografica senza introdurre perdita di venature o aloni.

## Vincoli

Nessuna sovrascrittura dei TIFF o degli output validati. Codice e immagini restano nel progetto locale; GitHub contiene soltanto documentazione.
