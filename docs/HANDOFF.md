# Handoff — Violin Reflection Removal

**Stato:** Fase 1 conclusa; Fase 2, Test 01 e Test 02 eseguiti. Risultato estetico ancora insufficiente.

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
- **Test 02, `2_reflection_step2.py`:** fusione automatica tramite cromaticità e luminosità. **4.872.007 pixel (10,72%) modificati**, alpha medio 0,148; riflessi ancora evidenti. Non è una correzione finale validata.

Output: `output/02_analisi_riflessi/test_01/` e `test_02/`.

## Prossimo passo — Test 03

**Creare localmente `2_reflection_step3.py`.** Prima di un'altra fusione, verificare se gli scatti registrati mostrino davvero texture del legno meglio leggibile nelle zone con riflesso. Testare l'intero violino, bordi compresi, con confronto a pixel nativi e zone di controllo. Generare una mappa diagnostica e pochi confronti leggibili.

**Decisione:** fusione selettiva solo se esistono dettagli recuperabili; altrimenti ripensare la tecnica.

## Regole

- Non usare codice/ROI degli esperimenti Codex; proseguire dal nostro percorso.
- Non sovrascrivere `images/`, Fase 1 o Test 01–02.
- Lavorare sui pixel nativi; ridurre soltanto le anteprime.
- Un esperimento alla volta; pochi output utili.
- Repository GitHub solo Markdown; immagini, codice e output **solo locali**.
