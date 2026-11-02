# Convenzioni per il codice

## Dove mettere il codice

- `code/phase1_registration/`: stime, controlli e pipeline geometrica consolidata.
- `code/phase2_reflection/`: confronti, fusioni e verifiche fotografiche.
- Eventuali funzioni davvero condivise potranno andare in `code/shared/` **solo quando servono**.

## Come commentare

Ogni script inizia con una breve scheda: **obiettivo, input, output, fasi, risultato atteso**. La docstring di una funzione spiega **cosa fa** e, se non è ovvio, **perché**. Nei blocchi importanti un commento chiarisce i criteri e i limiti; evitare commenti banali riga per riga.

Template sintetico:

```python
"""FASE N — Nome dell'esperimento.

Obiettivo: quale problema cerca di risolvere.
Input: fotografie o risultati già richiesti.
Output: file prodotti e cartella di destinazione.
Fasi: tre o quattro operazioni principali.
Risultato atteso: quale miglioramento si vuole verificare.
"""

def calcola_indicatore(immagine):
    """Calcola il valore usato per confrontare le zone candidate."""
    ...
```

## Template breve per documentare una fase

```markdown
# Fase N — Titolo

## Obiettivo
Quale problema risolviamo.

## Input e metodo
Quali scatti usiamo e come li elaboriamo.

## Risultato
Cosa cambia rispetto al test precedente; pochi dati verificabili.

## Limiti e decisione
Cosa non funziona, cosa conserviamo e perché.

## Prossimo passo
Un esperimento concreto da eseguire.
```

Documentare **soltanto risultati osservati**, distinguendo test tecnici e validazione estetica.

## Principi di manutenzione

- Un test = uno script; nomi coerenti con `test_01/`, `test_02/` ecc.
- Gli output approvati **non vengono sovrascritti**.
- Elaborazione dei TIFF a risoluzione nativa; resize solo per anteprime.
- Descrivere limiti ed euristiche: un punteggio non certifica un riflesso.
- Conservare gli script storici per ricostruire il ragionamento; usare `registration_pipeline.py` per la Fase 1 consolidata.
- Documentare il test dopo la valutazione, non presentarlo come riuscito in anticipo.

**Nota:** i commenti servono per comprendere il codice, non sostituiscono studio, verifiche e capacità di spiegarlo.
