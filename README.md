# Violin Reflection Removal

Documentazione del progetto di Computer Vision: ridurre i riflessi sulla superficie del violino, preservando colore, venature e aspetto naturale.

**Dataset locale:** `Base.tif` (4 luci accese), `Riflesso_1.tif`–`Riflesso_4.tif` (una luce ciascuno). TIFF 5504 × 8256 px.

## Avanzamento

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 · Acquisizione | [docs/00_acquisizione.md](docs/00_acquisizione.md) | Documentata |
| 1 · Registrazione | [docs/01_registrazione.md](docs/01_registrazione.md) | Completata e verificata |
| 2 · Riduzione fotografica dei riflessi | [docs/02_riduzione_riflessi.md](docs/02_riduzione_riflessi.md) | Test 02: attenuazione parziale visibile della macchia principale |

**Prossimo passo:** `2_reflection_step3.py` — partire dalla fusione del Test 02 e capire perché attenua la macchia principale più degli altri riflessi; verificare i dettagli disponibili nei donatori prima di migliorarla.

Per riprendere il lavoro: [docs/HANDOFF.md](docs/HANDOFF.md).

**Solo documentazione in GitHub:** codice Python, TIFF e output restano sul PC.
