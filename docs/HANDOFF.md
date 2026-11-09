# HANDOFF — Violin Reflection Removal

## Goal
Pipeline **generale** di riduzione fotografica dei riflessi usando scatti dello stesso soggetto con illuminazioni diverse. Il violino è il dataset di prova, **non una soluzione custom**. Serve una foto più bella, senza richiedere una decomposizione fisica rigorosa. [Dettagli](00_obiettivo.md).

## Disponibile in GitHub
- Fase 1: `code/phase1_registration/registration_pipeline.py` e i 6 script esplorativi originali di registrazione.
- Fase 2: `code/phase2_reflection/2_reflection_step1.py` … `2_reflection_step5b.py` (Test 05 e 05B inclusi).
- Convenzioni: [CONVENZIONI_CODICE.md](CONVENZIONI_CODICE.md).
- [Acquisizione](00_acquisizione.md), [registrazione](01_registrazione.md), [test](02_riduzione_riflessi.md), [slide del corso](03_slide_corso.md).

**Solo locali:** `images/`, `output/`, `codex_experiments/`. Non usare il lavoro Codex per proseguire. Non caricare TIFF su GitHub.

## Input originali
- `images/Base.tif` — tutte le quattro luci accese.
- `images/Riflesso_1.tif` … `Riflesso_4.tif` — una sola luce accesa per scatto.
- 5504 × 8256, RGB uint8.

## Fase 1 — validata
La pipeline `registration_pipeline.py` ha lasciato R1 (−0,843, −0,049 px), R2 (+0,350, +0,111), R3 (−0,236, −0,643) invariati e ha registrato R4 (−7,358, +0,269). Residuo mediano sul violino R4 circa **7,47 → 0,94 px**.

Usare gli output già presenti: `output/01_registrazione/test_01/risultato/registered/Riflesso_n_registered.tif` e `diagnostica/masks/Riflesso_n_valid.png`. Non rifare inutilmente la registrazione.

## Fase 2 — stato
- **Test 01:** panoramica delle cinque illuminazioni.
- **Test 02 — migliore attuale:** fusione, 4.872.007 pixel modificati (**10,72%**). Attenua il riflesso principale, resa naturale; rimangono riflessi altrove.
- **Test 03:** confronto a pixel nativi. Zona migliorata: Base−Test 02 **+21,52/255**. Selezione errata delle altre zone («ponticello» e «cordiera»).
- **Test 04:** maschera colore del legno e intensità maggiore. **12,29%** dei pixel modificati. **Visivamente preferito Test 02**; Test 04 è troppo legato al colore del violino.

- **Test 05:** confronto delle mappe candidate delle luci e di Base. Il 95,8% dei candidati Base ha una corrispondenza entro 5 px sulla mappa 1:8, **non è** una misura dell'accuratezza dei riflessi. La somma approssimata delle illuminazioni spiega solo parzialmente Base (R² holdout ~0,563). Molti falsi positivi su hardware, contorni e tavola colori.
- **Test 05B — eseguito e valutato:** 38.530 pixel candidati (5,43% anteprima); selezioni R1/R2/R3/R4: 7.535/7.886/4.761/18.348. Nonostante gli indizi di dettaglio, il massimo score 0,608 è sul **ponticello**: il donatore R1 introduce una forte ombra, non un miglioramento certo. Il secondo candidato (score 0,299) mostra una dominante violacea/lucida. **Falsi positivi** su corde, contorni, ponticello e tavola colori; la macchia diffusa alta a destra non domina le mappe. Non usare Test 05B per la fusione.

Output locali valutati: `output/02_analisi_riflessi/test_01/` … `test_05/` e `output/02_analisi_riflessi/test_05b/`. **Non sovrascriverli.**

## Prossima azione — progettare Test 05C (non eseguito)

1. Studiare **Top-hat morfologico e DoG a più scale** per picchi luminosi sottili e macchie diffuse; le scale vanno confrontate, non basta una soglia unica.
2. Usare **Sobel/Canny** per distinguere contorni rigidi (corde, ponticello, sagoma) dalla texture da recuperare, senza cancellare indiscriminatamente i bordi, anch'essi potenzialmente riflettenti.
3. Verificare il **confronto multi-illuminazione** e la coerenza dei dettagli dei donatori, penalizzando ombre e variazioni cromatiche e distinguendo le aree di controllo.
4. Produrre **solo mappe e ritagli** confrontabili con Test 05/05B. Tornare alla fusione soltanto se i falsi positivi diminuiscono e la macchia principale viene identificata meglio.

Riferimenti alle slide del corso: [03_slide_corso.md](03_slide_corso.md) (CV02–CV06, pagine PDF). Le proposte delle slide **non sono ancora risultati sperimentali**. Conservare Test 02 come baseline. La generalità su altri soggetti resta **non dimostrata**.

In futuro: parametri configurabili e applicazione, **non subito**.

## Uso dopo la riorganizzazione

Eseguire dalla radice locale: `python code/phase2_reflection/2_reflection_step3.py --help`. Gli script risolvono `images/` e `output/` rispetto alla radice, anche se sono dentro `code/`. Test 03 e 04 caricano Test 02 dalla stessa cartella; `registration_step2.py` importa `registration.py` dalla propria cartella. I percorsi degli output validati **non cambiano**. I file originali sono stati spostati sotto `code/` e commentati senza riprogettare i metodi.

## Regole
Un esperimento alla volta; foto, maschere e TIFF sempre locali; non modificare originali o output precedenti. Le misure di pixel modificati **non provano** la qualità estetica. Aggiornare la documentazione dopo ogni valutazione.
