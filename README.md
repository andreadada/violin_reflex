# Violin Reflection Removal

Documentazione del progetto di Computer Vision per migliorare la fotografia di un violino attenuando i riflessi indesiderati, senza perdere colore e venature.

## Dataset

Cinque TIFF a 5504 × 8256 px, conservati **solo in locale**:

- `Base.tif`: quattro luci accese.
- `Riflesso_1.tif`–`Riflesso_4.tif`: una luce accesa per scatto.

## Avanzamento

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 · Acquisizione | [docs/00_acquisizione.md](docs/00_acquisizione.md) | Documentata |
| 1 · Registrazione | [docs/01_registrazione.md](docs/01_registrazione.md) | Completata e verificata |
| 2 · Riduzione fotografica dei riflessi | [docs/HANDOFF.md](docs/HANDOFF.md) | In preparazione |

La registrazione è conclusa. Nella Fase 2 privilegiamo **la qualità estetica**, non la separazione fisica delle componenti luminose.

**Prossimo script locale:** `2_reflection_step1.py`, confronto visivo delle cinque fotografie registrate, senza modificare i TIFF.

Questo repository contiene solo `README.md` e `docs/`: nessuna immagine, script o output fotografico.
