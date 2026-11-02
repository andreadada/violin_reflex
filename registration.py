"""STEP 1 - Image Registration con Phase Correlation + ECC (sola traslazione).

Esegui: python registration.py

Confronta Base.tif e Riflesso_4.tif, misura gli spostamenti sulla tavola
colori e confronta la traslazione iniziale con il raffinamento ECC.

IMPORTANTE:
- Legge i TIFF a RISOLUZIONE ORIGINALE. Ogni crop e' di 640x640 pixel nativi.
- Le anteprime diagnostiche non sono TIFF registrati.
- Non altera ne' sovrascrive mai i TIFF di input.
- La versione corrente NON stima rotazione o scala: sara' lo step successivo.
"""

from pathlib import Path
import csv
import json
import cv2
import numpy as np

# ------------------------------------------------------
# BLOCCO 1: cartelle e regioni di analisi
# ------------------------------------------------------
ROOT = Path(__file__).resolve().parent
IMMAGINI = ROOT / "images"
OUTPUT = ROOT / "output" / "registration" / "step1_ecc"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Tutti i ritagli sono a risoluzione NATIVA, senza resize.
LATO = 640
MARGINE = 32  # Pixel extra: la traslazione non inventa bordi nel ritaglio.

# La tavola colori serve a CALIBRARE lo spostamento.
ZONE_TAVOLA = {
    "tavola_sx": (0.32, 0.915),
    "tavola_dx": (0.69, 0.915),
}

# Le zone del violino sono usate SOLO per verificare il risultato:
# non partecipano alla ricerca dei parametri di ECC.
ZONE_VERIFICA = {
    "alto_sx": (0.30, 0.17),
    "centro_sx": (0.35, 0.43),
    "centro_dx": (0.65, 0.43),
    "basso_dx": (0.68, 0.70),
}


def leggi_grigio(nome):
    """OpenCV legge tutti i pixel originali, senza ridimensionare."""
    path = IMMAGINI / nome
    immagine = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if immagine is None:
        raise FileNotFoundError(f"Non riesco a leggere {path}")
    return immagine


def estrai(foto, x_rel, y_rel, lato=LATO):
    """Ritaglia gli stessi pixel x,y da ciascuna fotografia."""
    h, w = foto.shape
    cx, cy = round(x_rel * w), round(y_rel * h)
    x0, y0 = cx - lato // 2, cy - lato // 2
    if x0 < 0 or y0 < 0 or x0 + lato > w or y0 + lato > h:
        raise ValueError(f"Ritaglio fuori dalla fotografia: ({x_rel},{y_rel})")
    return foto[y0:y0 + lato, x0:x0 + lato]


def sobel(foto):
    """Calcola il modulo del gradiente; non altera la fotografia originale."""
    smussata = cv2.GaussianBlur(foto, (3, 3), 0.5)
    f = smussata.astype(np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def fase(base, riflesso):
    """Trova la traslazione di 'riflesso' RISPETTO a 'base'."""
    a, b = sobel(base), sobel(riflesso)
    h, w = a.shape
    finestra = cv2.createHanningWindow((w, h), cv2.CV_32F)
    (dx, dy), risposta = cv2.phaseCorrelate(a, b, finestra)
    return float(dx), float(dy), float(risposta)


def normalizza_gradienti(gradiente):
    """Clipping solo per ECC: riduce l'influenza dei contorni estremi."""
    scala = max(float(np.percentile(gradiente, 99.5)), 1.0)
    return np.ascontiguousarray(np.clip(gradiente / scala, 0, 1), dtype=np.float32)


def raffina_ecc(base, riflesso, dx0, dy0):
    """Raffina una traslazione usando cv2.findTransformECC.

    ATTENZIONE AI SEGNI:
    - phaseCorrelate(A,B) stima la posizione di B rispetto ad A: (dx,dy).
    - findTransformECC(template=A,input=B) usa la matrice che mappa A -> B.
      Quindi l'inizializzazione e' +dx,+dy, NON -dx,-dy.
    - In warpAffine useremo poi il movimento opposto (-dx,-dy), oppure
      WARP_INVERSE_MAP con la matrice restituita da ECC.
    """
    a = normalizza_gradienti(sobel(base))
    b = normalizza_gradienti(sobel(riflesso))

    # Matrice 2x3: identita' + traslazione iniziale.
    warp = np.array([[1.0, 0.0, dx0],
                     [0.0, 1.0, dy0]], dtype=np.float32)
    criteri = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
              150, 1e-7)

    # MOTION_TRANSLATION evita di introdurre rotazioni in questo step.
    # ECC cerca di massimizzare la correlazione (Enhanced Correlation Coefficient).
    score, warp = cv2.findTransformECC(
        a, b, warp, cv2.MOTION_TRANSLATION, criteri,
        None, 5
    )
    return float(warp[0, 2]), float(warp[1, 2]), float(score)


def crop_corretto(foto, pos, dx, dy):
    """Sposta una copia del crop per la diagnostica, NON un TIFF.

    L'area presa dalla fotografia e' piu' grande di 640 pixel: con un
    margine di 32 px possiamo traslare ~7 px senza ricreare artificialmente
    i bordi del nostro quadrato di verifica.
    """
    xr, yr = pos
    largo = LATO + 2 * MARGINE
    extra = estrai(foto, xr, yr, largo)

    # Il contenuto di Riflesso_4 e' spostato di (+dx,+dy) rispetto a Base.
    # Per allinearlo applichiamo quindi (-dx,-dy).
    matrice = np.array([[1, 0, -dx], [0, 1, -dy]], dtype=np.float32)
    corretto = cv2.warpAffine(
        extra, matrice, (largo, largo),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    return corretto[MARGINE:MARGINE + LATO,
                    MARGINE:MARGINE + LATO]


def similarita_contorni(base, altra):
    """Correlazione lineare dei gradienti in una zona centrale del crop.

    E' una metrica ausiliaria: con luci diverse puo' essere fuorviante.
    Non indica una percentuale di pixel allineati.
    """
    a = sobel(base)[24:-24, 24:-24].ravel()
    b = sobel(altra)[24:-24, 24:-24].ravel()
    a = a - np.mean(a)
    b = b - np.mean(b)
    den = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / den) if den > 1e-10 else 0.0


def overlay_contorni(base, altra, scala):
    """Legenda dell'overlay: rosso=Base; ciano=Riflesso 4."""
    a = np.uint8(np.clip(sobel(base) * (255 / scala), 0, 255))
    b = np.uint8(np.clip(sobel(altra) * (255 / scala), 0, 255))
    return cv2.merge([b, b, a])  # Ordine BGR di OpenCV!


def pannello(immagine, titolo):
    """Crea una intestazione sopra il crop senza coprire i suoi pixel."""
    h, w = immagine.shape[:2]
    if len(immagine.shape) == 2:
        immagine = cv2.cvtColor(immagine, cv2.COLOR_GRAY2BGR)
    canvas = np.full((h + 65, w, 3), 24, dtype=np.uint8)
    canvas[65:, :] = immagine
    cv2.putText(canvas, titolo[:65], (12, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.53, (255, 255, 255),
                1, cv2.LINE_AA)
    cv2.putText(canvas, "Rosso=Base  Ciano=Riflesso4", (12, 51),
                cv2.FONT_HERSHEY_SIMPLEX, 0.43, (215, 215, 215),
                1, cv2.LINE_AA)
    return canvas


def main():
    # --------------------------------------------------
    # BLOCCO 2: carichiamo due TIFF, senza modificare file.
    # --------------------------------------------------
    base = leggi_grigio("Base.tif")
    riflesso = leggi_grigio("Riflesso_4.tif")
    if base.shape != riflesso.shape:
        raise ValueError(f"Dimensioni diverse: {base.shape} vs {riflesso.shape}")
    print("Risoluzione nativa (altezza, larghezza):", base.shape)

    # --------------------------------------------------
    # BLOCCO 3: stima iniziale dai due crop della tavola.
    # --------------------------------------------------
    misure_tavola = []
    for nome, pos in ZONE_TAVOLA.items():
        dx, dy, q = fase(estrai(base, *pos), estrai(riflesso, *pos))
        print(f"{nome}: phase dx={dx:+.3f}, dy={dy:+.3f}, risposta={q:.3f}")
        if q >= 0.20 and np.isfinite(dx) and np.isfinite(dy):
            misure_tavola.append((dx, dy))

    if len(misure_tavola) != 2:
        raise RuntimeError("Tavola colori: insufficienti misure affidabili (q>=0.20).")
    if np.linalg.norm(np.subtract(*misure_tavola)) > 2.0:
        raise RuntimeError("Le due misure della tavola differiscono oltre 2px.")
    dx_fase, dy_fase = np.median(np.array(misure_tavola), axis=0)

    # --------------------------------------------------
    # BLOCCO 4: ECC. Ottimizziamo SOLO sulla tavola sx.
    # --------------------------------------------------
    pos_train = ZONE_TAVOLA["tavola_sx"]
    try:
        dx_ecc, dy_ecc, score_ecc = raffina_ecc(
            estrai(base, *pos_train), estrai(riflesso, *pos_train),
            float(dx_fase), float(dy_fase))
        ecc_ok = (np.isfinite(dx_ecc) and np.isfinite(dy_ecc)
                  and np.hypot(dx_ecc - dx_fase, dy_ecc - dy_fase) <= 3.0)
        if not ecc_ok:
            print("ATTENZIONE: ECC diverge dalla stima iniziale. Non fidarsi del risultato!")
    except cv2.error as errore:
        print("ECC non e' convergente: non e' prova di immagine disallineata.")
        print(str(errore).splitlines()[0])
        dx_ecc, dy_ecc, score_ecc, ecc_ok = None, None, None, False

    print(f"\nPHASE  dx={dx_fase:+.3f}, dy={dy_fase:+.3f}")
    if ecc_ok:
        print(f"ECC    dx={dx_ecc:+.3f}, dy={dy_ecc:+.3f}, score={score_ecc:.4f}")
    else:
        print("ECC    non disponibile/da verificare: il confronto ECC sara' omesso")

    # --------------------------------------------------
    # BLOCCO 5: verifica su zone non usate per ECC.
    # --------------------------------------------------
    zone = {**ZONE_TAVOLA, **ZONE_VERIFICA}
    righe_csv = []
    righe_gray = []
    righe_sobel = []
    for nome, pos in zone.items():
        crop_a = estrai(base, *pos)
        crop_b = estrai(riflesso, *pos)
        crop_p = crop_corretto(riflesso, pos, float(dx_fase), float(dy_fase))
        crop_e = (crop_corretto(riflesso, pos, dx_ecc, dy_ecc)
                  if ecc_ok else crop_p)

        sim_b = similarita_contorni(crop_a, crop_b)
        sim_p = similarita_contorni(crop_a, crop_p)
        sim_e = similarita_contorni(crop_a, crop_e) if ecc_ok else float('nan')
        resid_p = fase(crop_a, crop_p)
        resid_e = fase(crop_a, crop_e) if ecc_ok else (float('nan'),) * 3
        righe_csv.append([nome, *fase(crop_a, crop_b), sim_b,
                          *resid_p, sim_p, *resid_e, sim_e])
        print(f"{nome:11s}  somiglianza: originale={sim_b:.3f}  "
              f"phase={sim_p:.3f}  ecc={sim_e:.3f}")

        scala = max(1.0, *(float(np.percentile(sobel(im), 99.5))
                           for im in (crop_a, crop_b, crop_p, crop_e)))
        o_b = overlay_contorni(crop_a, crop_b, scala)
        o_p = overlay_contorni(crop_a, crop_p, scala)
        o_e = overlay_contorni(crop_a, crop_e, scala)

        # Per mantenere le legende leggibili e la scala originale,
        # ogni pixel di ogni PNG rappresenta un pixel nativo del TIFF.
        righe_sobel.append(cv2.hconcat([
            pannello(o_b, nome + " - PRIMA"),
            pannello(o_p, nome + " - PHASE"),
            pannello(o_e, nome + " - ECC" if ecc_ok else nome + " - ECC NON DISP.")
        ]))
        righe_gray.append(cv2.hconcat([
            pannello(cv2.merge([crop_b, crop_b, crop_a]), nome + " - PRIMA"),
            pannello(cv2.merge([crop_p, crop_p, crop_a]), nome + " - PHASE"),
            pannello(cv2.merge([crop_e, crop_e, crop_a]), nome + " - ECC" if ecc_ok else nome + " - ECC NON DISP.")
        ]))

    # --------------------------------------------------
    # BLOCCO 6: report e anteprime, nessun TIFF scritto.
    # --------------------------------------------------
    destinazioni = [
        ("01_confronto_contorni.png", cv2.vconcat(righe_sobel)),
        ("02_confronto_grigi.png", cv2.vconcat(righe_gray)),
    ]
    for nome, immagine in destinazioni:
        percorso = OUTPUT / nome
        if not cv2.imwrite(str(percorso), immagine):
            raise IOError(f"Salvataggio fallito: {percorso}")
        print("PNG salvato:", percorso)

    intestazione = ["zona", "dx_prima", "dy_prima", "q_prima", "corr_prima",
                   "dx_phase_residuo", "dy_phase_residuo", "q_phase", "corr_phase",
                   "dx_ecc_residuo", "dy_ecc_residuo", "q_ecc", "corr_ecc"]
    with (OUTPUT / "03_risultati.csv").open("w", newline="", encoding="utf-8") as f:
        scrittore = csv.writer(f)
        scrittore.writerow(intestazione)
        scrittore.writerows(righe_csv)

    with (OUTPUT / "04_trasformazioni.json").open("w", encoding="utf-8") as f:
        json.dump({
            "note": "dx/dy descrivono Riflesso_4 rispetto a Base. Per correggere invertire il segno.",
            "phase": {"dx": float(dx_fase), "dy": float(dy_fase)},
            "ecc": ({"dx": float(dx_ecc), "dy": float(dy_ecc),
                     "score": float(score_ecc)} if ecc_ok else None),
            "ecc_ok_preliminary": bool(ecc_ok),
            "estimation_regions": list(ZONE_TAVOLA),
            "ecc_optimization_region": "tavola_sx",
            "verification_regions": list(ZONE_VERIFICA),
            "full_res_measurement": True,
            "original_tiff_modified": False
        }, f, indent=2, ensure_ascii=False)

    if ecc_ok:
        # Le zone del violino sono quelle realmente indipendenti dalla stima.
        val = [r for r in righe_csv if r[0] in ZONE_VERIFICA]
        med_p = float(np.median([r[8] for r in val]))
        med_e = float(np.median([r[12] for r in val]))
        print(f"\nMediana somiglianza sul violino: phase={med_p:.4f}, ecc={med_e:.4f}")
        print("NON scegliere automaticamente ECC: verificare anche le immagini.")

    print("\nSTEP 1 ECC completato: nessun TIFF originale modificato.")
    print("Risultati in:", OUTPUT)


if __name__ == "__main__":
    main()