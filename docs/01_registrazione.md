# 01 — Registrazione

**Stato: validata sul dataset.**

## Metodo

`Base.tif` è il riferimento immobile. Per ogni `Riflesso_n.tif`:

1. Stimare lo spostamento con **Phase Correlation** sui gradienti Sobel, usando due zone della tavola colori.
2. Confrontare le stime tra le due zone.
3. Per spostamenti rilevanti, verificare il miglioramento su aree indipendenti del violino.
4. Applicare una sola interpolazione al TIFF RGB originale, soltanto se la correzione è accettata.

La pipeline consolidata è `registration_pipeline.py`; gli script `registration.py` e `registration_step2.py`–`registration_step4.py` documentano le verifiche preliminari (ECC e tracking Lucas–Kanade).

## Risultati

| Scatto | Δx stimato | Δy stimato | Decisione |
| --- | ---: | ---: | --- |
| Riflesso 1 | −0,843 px | −0,049 px | Invariato |
| Riflesso 2 | +0,350 px | +0,111 px | Invariato |
| Riflesso 3 | −0,236 px | −0,643 px | Invariato |
| Riflesso 4 | −7,358 px | +0,269 px | Registrato |

La soglia operativa per non riscrivere scatti con spostamento ridotto è **1,5 px** (euristica, non misura di errore assoluto). Su Riflesso 4 il residuo mediano della verifica sui contorni del violino è sceso da circa **7,47 px a 0,94 px**.

## Output locale

`output/01_registrazione/test_01/risultato/registered/` contiene i TIFF registrati; le maschere dei pixel validi e i report accompagnano gli output.

## Limiti

La variazione dell'illuminazione può influenzare la correlazione e il tracking. La buona registrazione geometrica non implica equivalenza fotometrica. Gli scatti con piccoli spostamenti sono mantenuti identici, non certificati come perfettamente sovrapposti.
