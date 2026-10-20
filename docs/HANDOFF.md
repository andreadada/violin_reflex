# Handoff — Violin Reflection Removal

**Stato:** Fase 1 completata. Si riparte dalla progettazione della Fase 2.

## Obiettivo

Individuare e attenuare riflessi indesiderati sulla vernice del violino, conservando venature, colore e risoluzione della fotografia originale. Preferire procedure automatiche verificabili, con eventuale rifinitura manuale.

## Materiale

- `images/Base.tif`: riferimento, quattro luci accese.
- `images/Riflesso_1.tif`–`Riflesso_4.tif`: una luce accesa alla volta.
- Dimensioni: **5504 × 8256 px**, RGB a 8 bit per canale.

## Lavoro completato — Fase 1

| Script Python nel progetto locale | Scopo |
| --- | --- |
| `allineamento.py` | Primi overlay e gradienti Sobel |
| `verifica_allineamento.py` | Stime su più zone indipendenti |
| `registration.py` | Phase Correlation ed ECC traslazionale |
| `registration_step2.py` | Confronto con ECC euclideo/rotazione |
| `registration_step3.py` | Esportazione del TIFF registrato |
| `registration_step4.py` | Verifica con punti caratteristici e Lucas–Kanade |
| `registration_pipeline.py` | Pipeline consolidata per i quattro scatti |

### Risultati verificati

| Scatto | Δx | Δy | Esito |
| --- | ---: | ---: | --- |
| Riflesso 1 | −0,843 px | −0,049 px | Invariato |
| Riflesso 2 | +0,350 px | +0,111 px | Invariato |
| Riflesso 3 | −0,236 px | −0,643 px | Invariato |
| Riflesso 4 | −7,358 px | +0,269 px | Traslazione applicata |

Soglia prudenziale della pipeline: **1,5 px**. Per Riflesso 4, residuo mediano sui contorni del violino da **circa 7,47 px a 0,94 px**. Una soglia operativa non dimostra allineamento perfetto.

**Output conservato:**
`output/01_registrazione/test_01/`
- `risultato/registered/`: quattro TIFF riferiti a Base.
- `diagnostica/masks/`: maschere dei pixel validi.
- `report/`: risultati e misure.

Non ripetere la registrazione senza nuovi elementi che ne dimostrino la necessità.

## Prossimo lavoro — Fase 2

**Partire dalla teoria, non da una correzione già progettata.**

1. Distinguere le componenti di riflessione diffusa e speculare e discutere cosa è osservabile con quattro sorgenti separate.
2. Individuare segnali confrontabili tra le cinque immagini già registrate, tenendo conto del diverso livello di illuminazione.
3. Definire un piccolo esperimento diagnostico, con criteri di verifica prima di scrivere l'algoritmo.
4. Documentare parametri, limiti e risultato; soltanto dopo valutare un metodo di correzione.

**Nessun algoritmo di rimozione dei riflessi è validato nel percorso corrente.**

## Regole di lavoro

- Un esperimento alla volta: obiettivo → teoria → implementazione → verifica → conclusione.
- Nessuna modifica a `images/` o agli output validati.
- Calcoli e output fotografici a risoluzione nativa; eventuali resize solo per preview.
- Risultati leggeri e organizzati; niente nuove interfacce prima di aver verificato il metodo.
- Questo repository contiene soltanto `README.md` e documentazione in `docs/`.

**Perimetro:** il presente handoff riprende soltanto il percorso originale fino alla registrazione. Gli esperimenti successivi separati localmente non fanno parte di questa documentazione.
