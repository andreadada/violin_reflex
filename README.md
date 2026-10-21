# Violin Reflection Removal

Documentazione del progetto di Computer Vision: ridurre i riflessi sulla superficie del violino, preservando colore, venature e aspetto naturale.

**Dataset locale:** `Base.tif` (4 luci accese), `Riflesso_1.tif`–`Riflesso_4.tif` (una luce ciascuno). TIFF 5504 × 8256 px.

## Avanzamento

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 · Acquisizione | [docs/00_acquisizione.md](docs/00_acquisizione.md) | Documentata |
| 1 · Registrazione | [docs/01_registrazione.md](docs/01_registrazione.md) | Completata e verificata |
| 2 · Riduzione fotografica dei riflessi | [docs/02_riduzione_riflessi.md](docs/02_riduzione_riflessi.md) | Test 01–02 svolti; risultato non soddisfacente |

**Prossimo passo:** `2_reflection_step3.py` — verificare su tutto il violino, bordi inclusi, dove le singole illuminazioni conservino informazioni utili a rimuovere i riflessi. Nessuna nuova fusione prima di questa verifica.

Per riprendere il lavoro: [docs/HANDOFF.md](docs/HANDOFF.md).

**Solo documentazione in GitHub:** codice Python, TIFF e output restano sul PC.
