# Violin Reflection Removal

Documentazione del progetto di Computer Vision per studiare e ridurre i riflessi nelle fotografie di un violino, preservando il dettaglio del legno.

## Dataset

Cinque TIFF della stessa scena (5504 × 8256 px):

- `Base.tif`: quattro luci accese.
- `Riflesso_1.tif`–`Riflesso_4.tif`: una sola luce accesa per scatto.

## Avanzamento

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 · Acquisizione | [docs/00_acquisizione.md](docs/00_acquisizione.md) | Documentata |
| 1 · Registrazione | [docs/01_registrazione.md](docs/01_registrazione.md) | Completata e verificata |
| 2 · Analisi dei riflessi | Da sviluppare | Non iniziata in questo percorso |

La registrazione usa Base come riferimento, Phase Correlation su Sobel e verifica indipendente sul violino. `Riflesso_4` ha richiesto una traslazione; gli altri tre scatti sono rimasti invariati.

## Riprendere il lavoro

Leggere [docs/HANDOFF.md](docs/HANDOFF.md) per i file di riferimento, lo stato raggiunto e il prossimo esperimento.

Questo repository contiene **solo documentazione**. Codice, TIFF e risultati restano nel progetto locale. Le fasi successive saranno documentate qui soltanto dopo un esperimento verificato.
