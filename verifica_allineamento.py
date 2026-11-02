"""Verifica se Base.tif e Riflesso_1..4.tif sono allineati.

INSTALLAZIONE (nel terminale di PyCharm):
    pip install opencv-python numpy

ESECUZIONE:
    python verifica_allineamento.py

Lo script misura gli spostamenti; NON sposta, ritaglia o modifica i TIFF.
Tutti i confronti avvengono su piccoli ritagli di pixel ORIGINALI,
senza ridimensionare le immagini di partenza.
"""

from pathlib import Path
import csv

import cv2
import numpy as np


# 1) Percorsi: lo script sta nella cartella principale del progetto,
#    accanto alla sottocartella "images" che contiene i 5 TIFF originali.
CARTELLA = Path(__file__).resolve().parent
IMMAGINI = CARTELLA / "images"
RISULTATI = CARTELLA / "output" / "allineamento"
RISULTATI.mkdir(parents=True, exist_ok=True)

# 2) Dimensione dei ritagli: 640 x 640 pixel ORIGINALI.
#    Non riduciamo la risoluzione delle fotografie: analizziamo solo
#    alcune zone riconoscibili per evitare calcoli inutili su 45 MP.
LATO = 640

# 3) Centri delle zone, come frazioni della larghezza e dell'altezza.
#    Due zone sono sulla tavola colori (contiene bordi geometrici stabili),
#    altre sei sul violino. Zone con forti riflessi potrebbero essere inaffidabili:
#    per questo misuriamo varie regioni e confrontiamo i risultati.
ZONE = {
    "tavola_sinistra": (0.32, 0.915),
    "tavola_destra": (0.69, 0.915),
    "violino_alto_sx": (0.30, 0.17),
    "violino_alto_dx": (0.70, 0.17),
    "violino_centro_sx": (0.35, 0.43),
    "violino_centro_dx": (0.65, 0.43),
    "violino_basso_sx": (0.32, 0.70),
    "violino_basso_dx": (0.68, 0.70),
}


def leggi_grigio(percorso):
    # 4) La conversione in grigio serve SOLO a misurare i contorni.
    #    OpenCV legge il TIFF senza cambiarne le dimensioni.
    foto = cv2.imread(str(percorso), cv2.IMREAD_GRAYSCALE)
    if foto is None:
        raise FileNotFoundError(f"Impossibile leggere: {percorso}")
    return foto


def ritaglio(foto, x_rel, y_rel, lato):
    # 5) Estraiamo esattamente lo STESSO rettangolo dalle due foto.
    altezza, larghezza = foto.shape
    cx, cy = round(x_rel * larghezza), round(y_rel * altezza)
    x0, y0 = cx - lato // 2, cy - lato // 2
    x0 = max(0, min(larghezza - lato, x0))
    y0 = max(0, min(altezza - lato, y0))
    return foto[y0:y0 + lato, x0:x0 + lato]


def contorni(foto):
    # 6) I quattro scatti hanno LUCI differenti: confrontare direttamente
    #    la luminosità può dare un falso disallineamento.
    #    Con Sobel evidenziamo i contorni (venature, effe, scacchiera),
    #    relativamente più stabili dei valori di luminosità assoluti.
    smussata = cv2.GaussianBlur(foto, (3, 3), 0.5)
    f = smussata.astype(np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def misura_spostamento(base, altra):
    # 7) Phase correlation confronta i contorni e stima di QUANTI PIXEL
    #    la seconda immagine risulta spostata rispetto alla prima.
    #    Restituisce anche un indice di qualità ('risposta'), tipicamente
    #    vicino a 1 per una corrispondenza netta e più basso se ambigua.
    a, b = contorni(base), contorni(altra)
    finestra = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
    (dx, dy), risposta = cv2.phaseCorrelate(a, b, finestra)
    return float(dx), float(dy), float(risposta)


def salva_anteprima(base, altra, nome):
    # 8) Salviamo un controllo VISIVO su tre ritagli nativi.
    #    Rosso = Base, ciano = altra immagine: se i bordi si separano,
    #    possono esserci disallineamenti. Differenze di luce NON provano
    #    da sole un disallineamento.
    pannelli = []
    for zona in ("tavola_sinistra", "violino_centro_sx", "violino_alto_dx"):
        x, y = ZONE[zona]
        a = ritaglio(base, x, y, LATO).astype(np.uint8)
        b = ritaglio(altra, x, y, LATO).astype(np.uint8)
        # BGR OpenCV: canale rosso da Base, blu+verde dall'altra foto.
        confronto = np.dstack((b, b, a))
        cv2.putText(confronto, zona, (12, 32), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2, cv2.LINE_AA)
        pannelli.append(confronto)
    cv2.imwrite(str(RISULTATI / f"overlay_{nome}.png"), np.hstack(pannelli))


def esamina(base, altra, nome, righe):
    # 9) Una misura singola può sbagliare quando cambia il riflesso.
    #    Misuriamo perciò 8 aree e calcoliamo lo spostamento mediano.
    misure = []
    print(f"\n=== {nome} rispetto a Base ===")
    # L’overlay viene salvato anche quando i risultati numerici sono incerti.
    salva_anteprima(base, altra, nome)
    for zona, (x, y) in ZONE.items():
        a = ritaglio(base, x, y, LATO)
        b = ritaglio(altra, x, y, LATO)
        dx, dy, qualita = misura_spostamento(a, b)
        misure.append((zona, dx, dy, qualita))
        righe.append([nome, zona, f"{dx:.3f}", f"{dy:.3f}", f"{qualita:.3f}"])
        print(f"  {zona:21s} dx={dx:+7.2f}  dy={dy:+7.2f}  qualità={qualita:.2f}")

    # 10) Consideriamo solo le regioni con un picco di correlazione
    #     sufficientemente definito; le altre non sono prova di allineamento.
    affidabili = np.array([(dx, dy) for _, dx, dy, q in misure
                           if q >= 0.20 and np.isfinite(dx) and np.isfinite(dy)],
                          dtype=np.float64).reshape(-1, 2)
    if len(affidabili) < 3:
        print("  ESITO: NON CONCLUSIVO (troppe regioni poco affidabili).")
        return

    mediana = np.median(affidabili, axis=0)
    # Escludiamo eventuali zone dove il cambio di luce ha ingannato la misura.
    scarti = np.linalg.norm(affidabili - mediana, axis=1)
    coerenti = affidabili[scarti <= 2.0]
    if len(coerenti) < 3:
        print("  ESITO: NON CONCLUSIVO (misure troppo discordanti).")
        return

    dx, dy = np.median(coerenti, axis=0)
    dispersione = np.median(np.linalg.norm(coerenti - [dx, dy], axis=1))
    modulo = np.hypot(dx, dy)
    print(f"  Mediana: dx={dx:+.2f} px, dy={dy:+.2f} px; "
          f"spostamento={modulo:.2f} px; dispersione={dispersione:.2f} px")

    # 11) Le soglie sono INDICATIVE, non certificazioni metrologiche.
    if dispersione > 0.50 or len(coerenti) < len(affidabili) // 2 + 1:
        print("  ESITO: NON CONCLUSIVO: potrebbero esserci rotazioni, "
              "deformazioni o riflessi che falsano il confronto.")
    elif modulo <= 0.30:
        print("  ESITO: NESSUNO SPOSTAMENTO GLOBALE EVIDENTE (< 0.30 px).")
    else:
        print("  ESITO: POSSIBILE DISALLINEAMENTO: verificare gli overlay PNG.")


def main():
    # 12) Carichiamo Base una sola volta. Le altre foto vengono lette
    #     una alla volta, così non dobbiamo tenere 5 immagini da 45 MP in RAM.
    base = leggi_grigio(IMMAGINI / "Base.tif")
    if min(base.shape) < LATO:
        raise ValueError(f"Fotografie troppo piccole per ritagli da {LATO} px.")
    righe = []
    for numero in range(1, 5):
        nome = f"Riflesso_{numero}"
        altra = leggi_grigio(IMMAGINI / f"{nome}.tif")
        if altra.shape != base.shape:
            print(f"ATTENZIONE: {nome} ha dimensioni {altra.shape}, "
                  f"diverse da Base {base.shape}; NON confrontabile così.")
            continue
        esamina(base, altra, nome, righe)
        del altra

    # 13) CSV: utile per riportare al professore le misure per ogni zona.
    with open(RISULTATI / "misure_allineamento.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fotografia", "zona", "dx_pixel", "dy_pixel", "qualita"])
        writer.writerows(righe)
    print(f"\nRisultati salvati in: {RISULTATI}")
    print("NOTA: questo script è un controllo preliminare delle TRASLAZIONI, "
          "non verifica completamente rotazioni o deformazioni locali.")


if __name__ == "__main__":
    main()