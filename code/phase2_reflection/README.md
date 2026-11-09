# Fase 2 — Miglioramento estetico

**Scopo:** attenuare i riflessi di un soggetto fotografato con illuminazioni diverse, conservando colore e dettagli.

| Script | Ruolo | Esito |
| --- | --- | --- |
| `2_reflection_step1.py` | Confronto delle cinque illuminazioni | Diagnostica |
| **`2_reflection_step2.py`** | **Fusione fotografica selettiva** | **Baseline migliore attuale** |
| `2_reflection_step3.py` | Analisi dei donatori e di Test 02 | Diagnostica |
| `2_reflection_step4.py` | Maschera cromatica più restrittiva | Non preferito a Test 02 |
| `2_reflection_step5.py` | Corrispondenza dei candidati multi-luce | Diagnostica con falsi positivi |
| `2_reflection_step5b.py` | Confronto donatori, texture e controllo ombre | Valutato: falsi positivi su ponticello, corde, tavola colori |
| `2_reflection_step5c.py` | Top-hat/DoG multi-scala + penalità bordi | Valutato su TIFF: 11,95% candidati, falso positivo massimo sulla tavola colori |

Esecuzione dalla radice:

```bash
python code/phase2_reflection/2_reflection_step2.py --help
python code/phase2_reflection/2_reflection_step3.py --help
```

Le immagini originali restano in `images/`; registrati e maschere sono in `output/01_registrazione/test_01/`, risultati dei Test 01–05C in `output/02_analisi_riflessi/` (05C solo dopo esecuzione locale).

**Non confondere la riduzione della luminosità con la rimozione di un riflesso.** I Test 02 e 04 includono regole cromatiche legate al violino; la prossima fase deve ridurre questa dipendenza dal dataset.

**Prossimo:** creare una piccola validazione con zone annotate **solo per misurare** veri riflessi e falsi positivi, poi confrontare tutti i donatori a pixel nativi. Non iniziare la fusione senza risolvere i falsi positivi. Test 02 resta la migliore fotografia.
