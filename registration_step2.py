"""STEP 2 - Confronto registrazione: Phase, ECC traslazione, ECC Euclidean.

Esegui nella root del progetto: python registration_step2.py
Prerequisiti: registration.py dello Step 1, images/Base.tif, images/Riflesso_4.tif.

SOLO diagnostica: i TIFF originali non vengono modificati, e non vengono
ancora creati nuovi TIFF. Tutte le stime usano pixel alla risoluzione nativa.
"""

from pathlib import Path
import csv
import json
import math

import cv2
import numpy as np

# Importiamo le funzioni gia' spiegate nello Step 1.
# L'importazione NON esegue il suo main(), grazie al controllo __name__.
import registration as reg

OUT = Path(__file__).resolve().parent / "output" / "registration" / "step2_rotazione"
OUT.mkdir(parents=True, exist_ok=True)

# Solo queste due aree della tavola colori stimano la trasformazione.
# Le regioni del violino serviranno per la verifica INDIPENDENTE.
CALIBRAZIONE = reg.ZONE_TAVOLA
VERIFICA = reg.ZONE_VERIFICA
LATO = reg.LATO  # 640 px ORIGINALI, senza resize
MARGINE = 48  # pixel extra per non creare bordi falsi nei ritagli trasformati


def posizione_crop(shape, pos, lato=LATO):
    """Coordinate assolute (colonna,riga) dell'angolo in alto a sinistra."""
    h, w = shape
    cx, cy = round(pos[0] * w), round(pos[1] * h)
    x0, y0 = cx - lato // 2, cy - lato // 2
    if x0 < 0 or y0 < 0 or x0 + lato > w or y0 + lato > h:
        raise ValueError(f"Crop {pos} fuori dall'immagine di dimensioni {shape}")
    return x0, y0


def stima_fase(base, moving):
    """Mediana di dx,dy su DUE zone della tavola colori."""
    dati = []
    for nome, pos in CALIBRAZIONE.items():
        dx, dy, q = reg.fase(reg.estrai(base, *pos), reg.estrai(moving, *pos))
        print(f"  {nome:12s}: dx={dx:+.3f}, dy={dy:+.3f}, risposta={q:.3f}")
        if np.isfinite([dx, dy, q]).all() and q >= 0.20:
            dati.append((dx, dy))
    if len(dati) != 2 or np.linalg.norm(np.subtract(dati[0], dati[1])) > 2.0:
        raise RuntimeError("I due campioni della tavola non forniscono una stima affidabile.")
    dx, dy = np.median(np.asarray(dati), axis=0)
    return float(dx), float(dy)


def matrice_traslazione(dx, dy):
    """Mappa le coordinate di BASE nelle coordinate del RIFLESSO.

    p_riflesso = M * p_base. Per allineare si campiona la foto Riflesso
    in p_riflesso usando il flag cv2.WARP_INVERSE_MAP.
    """
    return np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)


def ROI_tavola(base):
    """Un unico rettangolo comprendente ENTRAMBI i quadrati della tavola.

    Si crea anche una maschera che considera SOLTANTO i due crop: il resto
    del rettangolo non contribuisce a ECC. La distanza fra i quadrati
    aiuta a stimare una rotazione piu' stabilmente rispetto a un solo crop.
    """
    angoli = [posizione_crop(base.shape, pos) for pos in CALIBRAZIONE.values()]
    x0 = min(p[0] for p in angoli)
    y0 = min(p[1] for p in angoli)
    x1 = max(p[0] + LATO for p in angoli)
    y1 = max(p[1] + LATO for p in angoli)
    maschera = np.zeros((y1-y0, x1-x0), dtype=np.uint8)
    for x, y in angoli:
        # Evitiamo gli ultimi pixel del bordo artificiale del crop.
        bordo = 8
        maschera[y-y0+bordo:y-y0+LATO-bordo,
                 x-x0+bordo:x-x0+LATO-bordo] = 255
    return (x0, y0, x1, y1), maschera


def ottimizza_ecc(base, moving, iniziale_globale, modello):
    """Raffina la registrazione usando ECC su ENTRAMBE le zone della tavola.

    OpenCV lavora sulle coordinate del rettangolo estratto. Una matrice
    globale non si puo' applicare direttamente a un ritaglio quando c'e'
    una rotazione: occorre effettuare il cambio di origine.

    W_local = T(-origine) @ W_global @ T(origine).
    Dopo l'ottimizzazione riconvertiamo W_local in coordinate globali.
    """
    (x0, y0, x1, y1), mask = ROI_tavola(base)
    a = reg.normalizza_gradienti(reg.sobel(base[y0:y1, x0:x1]))
    b = reg.normalizza_gradienti(reg.sobel(moving[y0:y1, x0:x1]))

    Wg = np.asarray(iniziale_globale, dtype=np.float64)
    A = Wg[:, :2]
    org = np.array([x0, y0], dtype=np.float64)
    # Conversione da globale a locale: t_local = A*origine + t_global - origine
    t_local = A @ org + Wg[:, 2] - org
    Wloc = np.column_stack([A, t_local]).astype(np.float32)

    criteri = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 110, 1e-6)
    score, Wloc = cv2.findTransformECC(
        a, b, Wloc, modello, criteri, mask, 5
    )

    A_new = Wloc[:, :2].astype(np.float64)
    # Conversione da locale a globale: t_glob = t_local + origine - A*origine
    t_global = Wloc[:, 2].astype(np.float64) + org - A_new @ org
    W_global = np.column_stack([A_new, t_global]).astype(np.float32)
    return W_global, float(score)


def controllo_plausibilita(W, W_phase, shape, rotazione=False):
    """Blocca esiti ECC matematicamente convergenti ma geometricamente assurdi.

    Per ogni centro usato in calibrazione e verifica, il modello ECC
    non deve deviare dalla previsione iniziale di oltre 4 pixel.
    La rotazione ammessa e' limitata a 0.15 gradi per questo esperimento.
    Le soglie sono euristiche, NON garanzie di registrazione corretta.
    """
    if W is None or not np.isfinite(W).all():
        return False, "matrice non finita"
    theta = math.degrees(math.atan2(float(W[1, 0]), float(W[0, 0])))
    if rotazione and abs(theta) > 0.15:
        return False, f"rotazione {theta:+.4f} gradi troppo grande"
    altezza, larghezza = shape
    for pos in {**CALIBRAZIONE, **VERIFICA}.values():
        xy = np.array([pos[0] * larghezza, pos[1] * altezza, 1.0], dtype=np.float64)
        delta = np.linalg.norm(W @ xy - W_phase @ xy)
        if delta > 4.0:
            return False, f"deviazione {delta:.2f} pixel dalla stima phase"
    return True, "plausibile (da verificare sui ritagli)"


def ritaglio_registrato(moving, pos, W):
    """Campiona il RIFLESSO nella griglia pixel del crop BASE.

    Usiamo una zona sorgente piu' grande di 640x640 per evitare bordi
    artificiali. W e' la matrice GLOBALE Base -> Riflesso. La conversione
    in coordinate locali segue:
      pos_sorgente_locale = A * pos_destinazione_locale +
                            A * top_left_base + t - top_left_extra.
    WARP_INVERSE_MAP significa che W_local mappa ogni pixel destinazione
    alla posizione da campionare nella sorgente.
    """
    x0, y0 = posizione_crop(moving.shape, pos)
    xe, ye = x0 - MARGINE, y0 - MARGINE
    lato_extra = LATO + 2*MARGINE
    if xe < 0 or ye < 0 or xe+lato_extra > moving.shape[1] or ye+lato_extra > moving.shape[0]:
        raise ValueError("Margine oltre i confini dell'immagine")
    extra = moving[ye:ye+lato_extra, xe:xe+lato_extra]
    A = W[:, :2].astype(np.float64)
    t = W[:, 2].astype(np.float64)
    orig = np.array([x0, y0], dtype=np.float64)
    local_t = A @ orig + t - np.array([xe, ye], dtype=np.float64)
    Wlocal = np.column_stack([A, local_t]).astype(np.float32)
    return cv2.warpAffine(
        extra, Wlocal, (LATO, LATO),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )


def valuta(base, moving, metodi):
    """Valutazione INDIPENDENTE sul violino; creazione griglie e CSV."""
    rows = []
    grid_edges, grid_gray = [], []
    nomi = ["Originale", "Phase", "ECC-trasl.", "ECC-rotaz."]
    for zona, pos in {**CALIBRAZIONE, **VERIFICA}.items():
        a = reg.estrai(base, *pos)
        original = reg.estrai(moving, *pos)
        campioni = [original] + [ritaglio_registrato(moving, pos, m) if m is not None else None
                                  for m in metodi[1:]]
        grad_a = reg.sobel(a)
        gradienti = [reg.sobel(b) if b is not None else None for b in campioni]
        scala = max(1.0, float(np.percentile(grad_a, 99.5)),
                    *(float(np.percentile(g, 99.5)) for g in gradienti if g is not None))
        panels_g, panels_c = [], []
        for nome, b, gb in zip(nomi, campioni, gradienti):
            if b is None:
                img_gray = np.full((LATO, LATO, 3), 24, dtype=np.uint8)
                img_edges = img_gray.copy()
                res_x, res_y, q, corr = (float("nan"),)*4
            else:
                res_x, res_y, q = reg.fase(a, b)
                corr = reg.similarita_contorni(a, b)
                vis_a = np.uint8(np.clip(grad_a * (255 / scala), 0, 255))
                vis_b = np.uint8(np.clip(gb * (255 / scala), 0, 255))
                img_edges = cv2.merge([vis_b, vis_b, vis_a])
                img_gray = cv2.merge([b, b, a])
            rows.append([zona, 'verifica' if zona in VERIFICA else 'calibrazione', nome,
                         res_x, res_y, q, corr])
            titolo = f"{zona} | {nome} | dx={res_x:+.2f} dy={res_y:+.2f}"
            panels_g.append(reg.pannello(img_gray, titolo))
            panels_c.append(reg.pannello(img_edges, titolo))
        grid_gray.append(cv2.hconcat(panels_g))
        grid_edges.append(cv2.hconcat(panels_c))
    return rows, cv2.vconcat(grid_edges), cv2.vconcat(grid_gray)


def scrivi_report(rows, mats, scores, phase, reason):
    with (OUT / '03_residui.csv').open('w', encoding='utf-8', newline='') as file:
        cw = csv.writer(file)
        cw.writerow(['zona', 'tipo_zona', 'metodo', 'dx_residuo', 'dy_residuo',
                     'risposta', 'corr_contorni'])
        cw.writerows(rows)

    summary = {}
    for nome in ('Originale', 'Phase', 'ECC-trasl.', 'ECC-rotaz.'):
        v = [r for r in rows if r[1]=='verifica' and r[2]==nome]
        # Media della correlazione (anche su zone poco affidabili).
        correlazioni = [r[6] for r in v if np.isfinite(r[6])]
        mean_corr = float(np.mean(correlazioni)) if correlazioni else None
        # Residuo su zone con risposta abbastanza alta; altre sono scartate.
        good = [math.hypot(r[3],r[4]) for r in v if r[5]>=0.12 and np.isfinite(r[3:6]).all()]
        summary[nome] = {
            'corr_mean': mean_corr,
            'residuo_median_px': float(np.median(good)) if good else None,
            'zone_residuo_affidabili': len(good),
        }
    data = {
        'note': 'Matrice W mappa le coordinate di Base verso Riflesso_4; applicazione: warpAffine con WARP_INVERSE_MAP. NON salvati TIFF.',
        'phase_dxdy': {'dx': phase[0], 'dy': phase[1]},
        'matrici_base_verso_riflesso': {k: v.tolist() if v is not None else None for k,v in mats.items()},
        'score_ecc': scores,
        'motivi_validazione_preliminare': reason,
        'verifica_indipendente': summary,
        'immagini_misurate_fullres': True,
        'tiff_originali_modificati': False,
    }
    (OUT / '04_trasformazioni.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return summary


def main():
    base = reg.leggi_grigio('Base.tif')
    moving = reg.leggi_grigio('Riflesso_4.tif')
    if base.shape != moving.shape:
        raise ValueError(f'Dimensioni diverse: {base.shape} vs {moving.shape}')
    altezza, larghezza = base.shape
    print(f'Risoluzione originale: {larghezza}x{altezza}')
    phase = stima_fase(base, moving)
    Wphase = matrice_traslazione(*phase)
    print(f'Phase: dx={phase[0]:+.4f}, dy={phase[1]:+.4f}')

    Wtranslation = None
    Weuclidean = None
    scores = {}
    reason = {}
    for nome, modello in [('ECC-trasl.', cv2.MOTION_TRANSLATION),
                          ('ECC-rotaz.', cv2.MOTION_EUCLIDEAN)]:
        try:
            # Inizializziamo entrambi dallo stesso modello Phase.
            W, score = ottimizza_ecc(base, moving, Wphase, modello)
            plausible, why = controllo_plausibilita(W, Wphase, base.shape,
                                                     rotazione=(modello==cv2.MOTION_EUCLIDEAN))
            print(f'{nome}: ECC score={score:.5f}, {why}')
            if plausible:
                if modello==cv2.MOTION_EUCLIDEAN: Weuclidean = W
                else: Wtranslation = W
            else:
                print(f'  {nome} scartato dalla visualizzazione; non valido geometricamente.')
            scores[nome] = float(score)
            reason[nome] = why
        except cv2.error as ex:
            print(f'{nome}: ECC non convergente: {str(ex).splitlines()[0]}')
            scores[nome] = None
            reason[nome] = 'ECC non convergente'
    if Weuclidean is not None:
        theta = math.degrees(math.atan2(float(Weuclidean[1,0]), float(Weuclidean[0,0])))
        print(f'Rotazione ECC: {theta:+.6f} gradi')
    mats = {'Phase': Wphase, 'ECC-trasl.': Wtranslation, 'ECC-rotaz.': Weuclidean}
    rows, g1, g2 = valuta(base, moving, [None, Wphase, Wtranslation, Weuclidean])
    for nome, img in [('01_confronto_contorni.png',g1), ('02_confronto_grigi.png',g2)]:
        p = OUT/nome
        if not cv2.imwrite(str(p), img): raise IOError(f'Impossibile salvare {p}')
        print('Salvato',p)
    summary = scrivi_report(rows, mats, scores, phase, reason)
    print('\nVerifica INDEPENDENTE sul violino:')
    for metodo, vals in summary.items():
        corr = vals['corr_mean']
        corr_txt = f'{corr:.4f}' if corr is not None else 'non disponibile'
        print(f"{metodo:13s}: media corr={corr_txt} | "
              f"mediana residuo={vals['residuo_median_px']} | "
              f"zone q>=0.12={vals['zone_residuo_affidabili']}/4")
    print('\nStep 2 completato: nessun TIFF registrato o sovrascritto.')
    print('Output:',OUT)


if __name__=='__main__':
    main()