# Handoff — Violin Reflection Removal

**Stato:** Fase 1 conclusa. Fase 2: Test 01–03 eseguiti, Test 04 preparato ma non ancora valutato sulle foto reali. Test 02 attenua visibilmente la macchia principale.

## Obiettivo

Ottenere una fotografia bella da catalogo, riducendo i riflessi su **tutto il violino, bordi inclusi**, senza perdere colore o venature. Il docente non richiede una separazione fisica delle componenti luminose.

## Input locali

- `images/Base.tif` — tutte e quattro le luci accese.
- `output/01_registrazione/test_01/risultato/registered/Riflesso_1_registered.tif` … `Riflesso_4_registered.tif`.
- Maschere di validità in `output/01_registrazione/test_01/diagnostica/masks/`.
- TIFF 5504 × 8256 px, RGB uint8.

## Fase 1 — Registrazione (validata)

Script originali: `allineamento.py`, `verifica_allineamento.py`, `registration.py`, `registration_step2.py`, `registration_step3.py`, `registration_step4.py`, `registration_pipeline.py`.

| Scatto | Δx | Δy | Decisione |
| --- | ---: | ---: | --- |
| R1 | −0,843 px | −0,049 px | Invariato |
| R2 | +0,350 px | +0,111 px | Invariato |
| R3 | −0,236 px | −0,643 px | Invariato |
| R4 | −7,358 px | +0,269 px | Registrato |

Soglia operativa **1,5 px**. Residuo mediano di R4 sui contorni: circa **7,47 → 0,94 px**. Non rifare la registrazione.

## Fase 2 — Test eseguiti

Dettagli: [02_riduzione_riflessi.md](02_riduzione_riflessi.md).

- **Test 01, `2_reflection_step1.py`:** confronto delle cinque illuminazioni, nessuna correzione. Base è il riferimento più equilibrato.
- **Test 02, `2_reflection_step2.py`:** fusione automatica tramite cromaticità e luminosità. **4.872.007 pixel (10,72%) modificati**, alpha medio 0,148. **Attenuazione parziale visibile della macchia principale** con resa generale abbastanza naturale; altri riflessi persistono. Prima candidata promettente.
- **Test 03, `2_reflection_step3.py`:** confronto di quattro aree a pixel nativi. Riduzione luminosa media **21,52/255** sulla zona migliorata; selezione automatica poco affidabile nelle aree denominate «riflesso residuo» (ponticello) e «bordo» (cordiera). Nessuna nuova correzione.

Output locali: `output/02_analisi_riflessi/test_01/`, `test_02/`, `test_03/`.

## Prossimo passo — Test 04

**Eseguire localmente `2_reflection_step4.py`**, che riutilizza l'algoritmo Test 02 e aggiunge una protezione cromatica del legno, escludendo dove possibile corde, ponticello e cordiera. La forza aumenta moderatamente solo per i candidati già individuati. Il codice ha superato un test tecnico sintetico, **non una verifica estetica sul dataset reale**.

Output nuovo: `output/02_analisi_riflessi/test_04/` (TIFF, prima/Test 02/Test 04, mappa, maschera, report). Confrontare macchia principale, bordi, effe e legno sano al 100%. Evitare ulteriori aumenti di forza se compaiono aloni o scurimenti.

## Regole

- Non usare codice/ROI degli esperimenti Codex; proseguire dal nostro percorso.
- Non sovrascrivere `images/`, Fase 1 o Test 01–02.
- Lavorare sui pixel nativi; ridurre soltanto le anteprime.
- Un esperimento alla volta; pochi output utili.
- Repository GitHub solo Markdown; immagini, codice e output **solo locali**.
