# Handoff — Violin Reflection Removal

**Stato:** Fase 1 completata. Si riparte dalla progettazione della Fase 2.

## Obiettivo

Individuare e attenuare riflessi indesiderati sulla vernice del violino, conservando venature, colore e risoluzione della fotografia originale. Preferire procedure automatiche verificabili, con eventuale rifinitura manuale.

## Materiale

- `images/Base.tif`: riferimento, quattro luci accese.
- `images/Riflesso_1.tif`–`Riflesso_4.tif`: una luce accesa alla volta.
- Dimensioni: **5504 × 8256 px**, RGB a 8 bit per canale.

## Fase 1 — Registrazione completata

Gli script originali sono `allineamento.py`, `verifica_allineamento.py`, `registration.py`, `registration_step2.py`, `registration_step3.py`, `registration_step4.py` e `registration_pipeline.py`.

| Scatto | Δx | Δy | Esito |
| --- | ---: | ---: | --- |
| Riflesso 1 | −0,843 px | −0,049 px | Invariato |
| Riflesso 2 | +0,350 px | +0,111 px | Invariato |
| Riflesso 3 | −0,236 px | −0,643 px | Invariato |
| Riflesso 4 | −7,358 px | +0,269 px | Registrato |

Soglia prudenziale: **1,5 px**. Su Riflesso 4 il residuo mediano sui contorni del violino è passato da circa **7,47 px a 0,94 px**.

Output confermati:
`output/01_registrazione/test_01/risultato/registered/` (TIFF);
`diagnostica/masks/` (pixel validi);
`report/` (misure).

## Fase 2 — Miglioramento estetico (da iniziare)

Indicazione del docente: non serve separare fisicamente le componenti luminose; serve una fotografia esteticamente migliore. La registrazione iniziale richiesta è già stata eseguita.

**Step 2.1 — `2_reflection_step1.py` (locale, ancora da creare):**
1. Leggere Base e i quattro TIFF registrati.
2. Produrre un confronto visivo delle cinque illuminazioni senza correzioni.
3. Identificare le zone con riflessi fotograficamente fastidiosi.
4. Usare le osservazioni per scegliere il primo intervento di riduzione dei riflessi.

Output previsto: `output/02_analisi_riflessi/test_01/`. Nessun file originale va modificato; nessuna fusione o rimozione nel primo step.

## Regole

- Proseguire **dal nostro codice originale**, senza recuperare algoritmi o ROI degli esperimenti Codex.
- Un esperimento alla volta: obiettivo, metodo, risultati e conclusione.
- Conservare la risoluzione nativa per i dati; resize soltanto delle anteprime.
- Repository GitHub: **solo documentazione**. TIFF, codice Python e output restano sul PC.
