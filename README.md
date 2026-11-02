# Violin Reflection Removal

Pipeline di Computer Vision per **ridurre i riflessi e migliorare esteticamente** fotografie multi-scatto dello stesso soggetto con illuminazioni diverse. Il violino è il primo dataset, non il limite dell'algoritmo.

## Documentazione
- [Obiettivo e criteri](docs/00_obiettivo.md)
- [Acquisizione](docs/00_acquisizione.md)
- [Fase 1: registrazione](docs/01_registrazione.md) — validata
- [Fase 2: esperimenti](docs/02_riduzione_riflessi.md) — Test 01–04
- [HANDOFF](docs/HANDOFF.md) — stato, decisioni e prossimi passi

**Baseline attuale: Test 02.** Attenua visibilmente il riflesso principale conservando un aspetto naturale. Il Test 04 non è preferito e introduce una maschera cromatica più specifica del violino.

## Codice del nostro percorso
- Fase 1: `registration_pipeline.py` (pipeline consolidata); `allineamento.py`, `verifica_allineamento.py`, `registration.py`, `registration_step2.py`, `registration_step3.py`, `registration_step4.py` (sviluppo e verifiche).
- Fase 2: `2_reflection_step1.py` fino a `2_reflection_step4.py`.

Installazione: `pip install -r requirements.txt`. Gli script vanno eseguiti nella root del progetto; non rigenerare la Fase 1 se gli output validati sono già disponibili.

**Dataset e risultati soltanto sul PC:** `images/`, `output/`, `codex_experiments/` non sono caricati su GitHub. La documentazione riporta le osservazioni e le misure, ma il codice da solo non riproduce gli output senza i TIFF locali.

Il focus è la qualità visiva, **non** una separazione fisica rigorosa delle componenti della luce.
