# Violin Reflection Removal

Pipeline di Computer Vision per attenuare i riflessi in **più fotografie dello stesso soggetto con luci differenti**. Il violino è il primo dataset, non il limite dell'algoritmo. Obiettivo: una fotografia più bella e naturale, non una decomposizione fisica rigorosa della luce.

## Avanzamento

- **Fase 1 — Registrazione:** completata e validata. Script principale: `code/phase1_registration/registration_pipeline.py`.
- **Fase 2 — Riduzione dei riflessi:** Test 01–05C eseguiti e valutati sui TIFF reali; **Test 02** resta la migliore fotografia. I Test 05/05B/05C sono solo diagnostici e hanno falsi positivi.
- **Test 05C valutato:** 84.857 candidati (11,95% preview); prima selezione errata sulla tavola colori, secondo candidato plausibile in alto a destra. **Prossimo:** piccolo insieme di zone annotate per valutare precisione e donatori, non nuova fusione.

## Struttura

```text
code/
  phase1_registration/  # registrazione e verifiche storiche
  phase2_reflection/    # Test 01–05C
docs/                  # obiettivo, acquisizione, risultati, handoff
images/                # SOLO LOCALE: TIFF originali
output/                # SOLO LOCALE: TIFF registrati e test
```

Gli script leggono `images/` e `output/` dalla **radice del progetto**, anche se il codice è organizzato in `code/`. Eseguire dal terminale PyCharm aperto nella radice:

```bash
pip install -r requirements.txt
python code/phase2_reflection/2_reflection_step2.py --help
python code/phase2_reflection/2_reflection_step3.py --help
python code/phase2_reflection/2_reflection_step5c.py --help
```

**Attenzione:** il Test 02 produce `output/02_analisi_riflessi/test_02/`; se esiste già, non rilanciarlo senza scegliere un `--out` nuovo. I Test 03–04 caricano Test 02 dalla stessa cartella; Test 05B riutilizza Test 05; Test 05C riutilizza Test 05 e 05B (nella stessa cartella).

## Documentazione

1. [Obiettivo generale](docs/00_obiettivo.md)
2. [Acquisizione](docs/00_acquisizione.md)
3. [Registrazione](docs/01_registrazione.md)
4. [Esperimenti sui riflessi](docs/02_riduzione_riflessi.md)
5. [Spunti dalle slide del corso](docs/03_slide_corso.md)
6. [Regole per i commenti](docs/CONVENZIONI_CODICE.md)
7. **[HANDOFF: stato e prossimo passo](docs/HANDOFF.md)**

GitHub contiene **script Python e documentazione**. Le fotografie e gli output restano esclusivamente sul PC; `codex_experiments/` non fa parte del lavoro corrente.
