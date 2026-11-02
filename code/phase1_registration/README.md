# Fase 1 — Registrazione

**Scopo:** stimare e correggere, quando necessario, piccoli disallineamenti tra Base e i quattro scatti con luci separate.

| File | Ruolo |
| --- | --- |
| `allineamento.py` | Prime prove e diagnostiche (storico; esegue il codice anche all'importazione) |
| `verifica_allineamento.py` | Misure su più regioni |
| `registration.py` | Phase Correlation + ECC traslazionale |
| `registration_step2.py` | Confronto traslazione/rotazione |
| `registration_step3.py` | Esportazione TIFF registrato di Riflesso 4 |
| `registration_step4.py` | Verifica con Lucas–Kanade |
| **`registration_pipeline.py`** | **Pipeline consolidata** dei quattro scatti |

Esecuzione dalla radice: `python code/phase1_registration/registration_pipeline.py --help`.

**Risultato validato:** R1–R3 invariati; R4 registrato (residuo mediano ~7,47 → 0,94 px). I TIFF pronti sono in `output/01_registrazione/test_01/risultato/registered/`.

**Non ripetere la Fase 1** se gli output sono già presenti. Gli script storici restano utili per studiare le scelte, ma non sono la via ordinaria per la Fase 2.
