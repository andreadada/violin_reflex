# 05 — Fotografia da catalogo

**Stato: obiettivo non ancora raggiunto.**

## Obiettivo

Produrre un'immagine del violino adatta a un catalogo: illuminazione leggibile, colore credibile, texture autentica e riflessi indesiderati ridotti, senza introdurre aloni, sfocature o dettagli inventati.

## Riferimento

`Final.tif` è stato esaminato come riferimento estetico, previa registrazione diagnostica rispetto a Base e conversione colore Adobe RGB → sRGB per il confronto. Non è noto un processo di generazione che lo renda utilizzabile come verità a terra della rimozione dei riflessi.

## Esperimenti

Sono state esaminate correzioni globali e locali, combinazioni di illuminazioni e varianti multiscala. Diverse prove hanno introdotto scurimento, perdita di dettaglio, aloni o alterazioni cromatiche.

Una candidata con circa **+0,10 EV** e saturazione **×0,97** modificava quasi tutti i pixel, ma **non** dimostrava una riduzione dei riflessi.

## Criterio di accettazione

Una candidata sarà considerata migliore soltanto se un confronto visivo a pixel nativi mostra:

- attenuazione effettiva di un difetto identificato;
- mantenimento delle venature e del colore plausibile;
- assenza di bordi di fusione e nuovi artefatti.

## Prossimo passo

Confrontare la stessa macchia in Base e nei quattro donatori registrati, prima di implementare ulteriori correzioni. Se nessun donatore contiene dati utilizzabili, rivalutare il metodo anziché forzare una fusione.
