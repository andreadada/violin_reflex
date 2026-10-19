# 02 — Diagnostica dei riflessi

**Stato: esplorativa; nessun riflesso rimosso.**

## Metodo

`reflection_diagnostics_phase2.py` confronta Base con i quattro scatti registrati:

- Ricava da Base una maschera cromatica indicativa della zona di legno.
- Esclude contorni e pixel senza dati validi dopo la registrazione.
- Calcola una luminanza approssimata **Y′** sui valori RGB codificati.
- Misura il rapporto locale di luminanza donatore/Base:

```text
raw = log2((Y_donatore + 8) / (Y_Base + 8))
local = raw - media_locale(raw)
```

La finestra locale predefinita è **257 × 257 px nativi**. Le soglie iniziali delle anomalie sono **0,30 stop** sul rapporto grezzo e **0,20 stop** sul residuo locale. Mappe e maschere vengono prodotte a risoluzione nativa; le composizioni panoramiche sono anteprime.

## Interpretazione

Una differenza di luminosità **non identifica automaticamente un riflesso speculare**. La mappa «Base più luminosa di almeno due donatori» identifica una differenza ripetuta, non un difetto certo.

## Limiti osservati

- Riflessi ampi possono essere assorbiti dalla stima della variazione lenta.
- Il cambio di luce modifica anche le componenti diffuse e il colore percepito.
- Il confronto usa valori RGB gamma-codificati, non misure radiometriche calibrate.
- Una maschera candidata deve essere verificata visivamente prima di qualsiasi correzione.

**Esito:** diagnostiche utili a localizzare differenze, insufficienti per una rimozione automatica affidabile.
