# Obiettivo del progetto

## Problema
Disponiamo di più fotografie **dello stesso soggetto, con la stessa geometria e illuminazioni differenti**. Riflessi fastidiosi ne compromettono l'aspetto.

Il violino è il **dataset iniziale**, non l'unico oggetto che l'algoritmo deve saper gestire.

## Goal
Costruire una pipeline che:
1. allinei automaticamente le immagini;
2. confronti le informazioni fra illuminazioni;
3. attenui i riflessi su **tutta la superficie**, compresi i bordi;
4. conservi texture, colori e un risultato naturale;
5. supporti in futuro parametri configurabili e una GUI per la calibrazione finale.

L'indicazione del professore è ottenere una **foto bella**, non separare fisicamente in modo rigoroso luce diffusa e speculare. Ha richiesto di verificare l'allineamento iniziale, già completato.

## Criteri di valutazione
- Attenuazione visibile dei riflessi, non soltanto pixel più scuri.
- Nessuna perdita evidente di venature, alterazione di colore o aloni.
- Metodi **riutilizzabili**: evitare soglie fisse per il legno arancione e ROI specifiche del violino.
- Misure tecniche e confronto a pixel nativi, ma decisione finale basata anche sull'aspetto fotografico.

## Perimetro e limiti
Sono richiesti scatti multipli (non una sola foto). Non si possono inventare dettagli che mancano in tutte le illuminazioni. Il funzionamento su soggetti differenti **non è ancora verificato**.

**Direzione:** continuare dal Test 02, non dal Test 04, e generalizzare il rilevamento/fusione prima di costruire un'interfaccia.
