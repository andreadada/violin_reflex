# HANDOFF — Violin Reflection Removal

## Goal
Pipeline **generale** di riduzione fotografica dei riflessi usando scatti dello stesso soggetto con illuminazioni diverse. Il violino è il dataset di prova, **non una soluzione custom**. Serve una foto più bella, senza richiedere una decomposizione fisica rigorosa. [Dettagli](00_obiettivo.md).

## Disponibile in GitHub
- Fase 1: `code/phase1_registration/registration_pipeline.py` e i 6 script esplorativi originali di registrazione.
- Fase 2: `code/phase2_reflection/2_reflection_step1.py` … `2_reflection_step5c.py` (Test 01–05C inclusi).
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

- **Test 05C — eseguito e valutato sui TIFF reali:** 84.857 pixel candidati (**11,95%** del frame preview 1:8), contro 38.530 (**5,43%**) di Test 05B. Scelte R1–R4: 10.369 / 13.179 / 9.408 / 51.901 (**R4: 61,2%**). Il massimo score **0,514** è sulla **tavola colori**: falso positivo, supporto non cromatico include un oggetto non target. Un secondo candidato **(3444,2964), R4, score 0,469** è nella zona di legno alta a destra con Base visivamente slavata: promettente da esaminare, **non** prova di donatore migliore. Microcontrasto Base→donatore 0,0115→0,0053: il contrasto da riflesso può falsare la metrica. I filtri multiscala rispondono ancora a contorni/texture/hardware. Nessun nuovo TIFF.

Output locali già valutati: `output/02_analisi_riflessi/test_01/` … `test_05/`, `test_05b/`, `test_05c/`. Non sovrascriverli.

## Prossima azione — protocollo di valutazione controllato

**Non** aumentare altre soglie o passare subito a un Test 06 di fusione. Predisporre **pochi esempi annotati soltanto per valutare**: riflesso diffuso in alto a destra, riflessi residui, bordi, corde/ponticello, legno sano e tavola colori. Per ognuno esaminare Base + R1–R4 a pixel nativi e valutare il recupero fotografico di texture, colore e ombre. Le etichette manuali **non sono input dell'algoritmo finale**. Separare prima il problema **supporto del soggetto** da quello di **rilevamento del riflesso** e dalla **scelta del donatore**. Poi decidere un'unica modifica verificabile, senza soglie cromatiche specifiche per il violino.

I Test 05/05B/05C sono **diagnostici**. Le mappe di score non sono probabilità e le percentuali dei candidati non misurano la precisione. **Test 02 rimane la baseline preferita visivamente.** Obiettivo generale: foto di riferimento ben illuminata + acquisizioni alternative, non una soluzione custom per questo violino.

In futuro: parametri configurabili e applicazione, non ora.

## Uso dopo la riorganizzazione

Eseguire dalla radice locale: `python code/phase2_reflection/2_reflection_step3.py --help`. Gli script risolvono `images/` e `output/` rispetto alla radice, anche se sono dentro `code/`. Test 03 e 04 caricano Test 02 dalla stessa cartella; `registration_step2.py` importa `registration.py` dalla propria cartella. I percorsi degli output validati **non cambiano**. I file originali sono stati spostati sotto `code/` e commentati senza riprogettare i metodi.

## Regole
Un esperimento alla volta; foto, maschere e TIFF sempre locali; non modificare originali o output precedenti. Le misure di pixel modificati **non provano** la qualità estetica. Aggiornare la documentazione dopo ogni valutazione.
