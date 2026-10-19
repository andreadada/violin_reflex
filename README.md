# Violin reflection removal

Documentazione del lavoro di Computer Vision per ridurre i riflessi indesiderati nelle fotografie di un violino, preservando colore, venature e dettagli della vernice.

Il progetto usa cinque scatti della stessa scena: `Base.tif` con quattro luci accese e `Riflesso_1.tif`–`Riflesso_4.tif` con una sola luce accesa per scatto.

## Fasi

| Fase | Documento | Stato |
| --- | --- | --- |
| 0 | [Dati e acquisizione](docs/00_acquisizione.md) | Documentata |
| 1 | [Registrazione](docs/01_registrazione.md) | Validata sul dataset |
| 2 | [Analisi dei riflessi](docs/02_diagnostica_riflessi.md) | Diagnostica, non rimozione |
| 3 | [Analisi RAW](docs/03_analisi_raw.md) | Esplorativa |
| 4 | [Correzione locale](docs/04_correzione_locale.md) | Non validata |
| 5 | [Fotografia da catalogo](docs/05_fotografia_catalogo.md) | Non conclusa |

## Stato attuale

La registrazione geometrica è stata verificata. Le prove di correzione successive hanno evidenziato un limite: ridurre la luminosità di una zona non significa necessariamente eliminare un riflesso. **Non è stata ancora ottenuta una fotografia finale con rimozione dei riflessi validata.**

Prossimo esperimento: confrontare, a pixel nativi, una stessa macchia in Base e nei quattro scatti registrati per verificare se esista una sorgente con informazione fotografica più pulita.

## Convenzioni

- Sorgenti e risultati fotografici restano nel progetto locale; **questo repository contiene solo documentazione**.
- Ogni fase distingue metodo, osservazioni e limiti.
- Nessun risultato di diagnostica è presentato come prova di rimozione del riflesso.
- Le fotografie originali non vengono sovrascritte.

Ultimo aggiornamento: 19 ottobre 2026.
