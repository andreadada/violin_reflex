# 00 — Acquisizione

## Obiettivo

Fotografare lo stesso violino con illuminazioni diverse per individuare riflessi indesiderati senza perdere la trama originale del legno.

## Dataset

| File | Illuminazione |
| --- | --- |
| `Base.tif` | Tutte e quattro le luci accese |
| `Riflesso_1.tif` | Solo luce 1 |
| `Riflesso_2.tif` | Solo luce 2 |
| `Riflesso_3.tif` | Solo luce 3 |
| `Riflesso_4.tif` | Solo luce 4 |

I cinque TIFF condividono la risoluzione **5504 × 8256 px** (circa 45,4 MP); la pipeline di registrazione li gestisce come immagini RGB a 8 bit. Sono disponibili anche i corrispondenti file Nikon NEF.

## Metadati RAW rilevati

Nikon Z8, 50 mm, ISO 160, 1/125 s, f/11, compensazione +2/3 EV, bilanciamento del bianco manuale, RAW a 14 bit lossless. Livelli RAW analizzati: nero 1008, bianco 16383.

## Vincoli

- Non modificare gli scatti originali.
- Preservare la risoluzione nativa nelle misure e negli output fotografici.
- Ridurre le immagini solo per le anteprime.
- Non assumere che la somma dei singoli scatti ricostruisca automaticamente Base.

Il file `Final.tif` è una fotografia ritoccata di riferimento estetico, **non** una ground truth della componente speculare.
