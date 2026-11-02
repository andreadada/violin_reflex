# Violin Reflection Removal

Documentazione del progetto di Computer Vision: ridurre i riflessi sulla superficie del violino, preservando colore, venature e aspetto naturale.

**Dataset locale:** `Base.tif` (4 luci accese), `Riflesso_1.tif`–`Riflesso_4.tif` (una luce ciascuno). TIFF 5504 × 8256 px.

## Avanzamento

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 · Acquisizione | [docs/00_acquisizione.md](docs/00_acquisizione.md) | Documentata |
| 1 · Registrazione | [docs/01_registrazione.md](docs/01_registrazione.md) | Completata e verificata |
| 2 · Riduzione fotografica dei riflessi | [docs/02_riduzione_riflessi.md](docs/02_riduzione_riflessi.md) | Test 01–03 svolti; Test 04 pronto da provare |

**Prossimo passo locale:** `2_reflection_step4.py` — evoluzione del Test 02: maschera del legno più selettiva e intensità moderatamente maggiore. Il Test 03 ha mostrato che la ricerca automatica delle zone confondeva anche ponticello e cordiera. Valutare il nuovo risultato a zoom 100% prima di considerarlo un miglioramento.

Per riprendere il lavoro: [docs/HANDOFF.md](docs/HANDOFF.md).

**Solo documentazione in GitHub:** codice Python, TIFF e output restano sul PC.
