"""STEP 3 — Applica una sola volta la traslazione Phase a Riflesso_4.tif.

Questo programma NON stima nuovamente l'allineamento: legge la matrice
selezionata e gia' verificata nello Step 2 (04_trasformazioni.json).

- Sorgente: images/Riflesso_4.tif
- Riferimento: images/Base.tif
- Output: output/registered/Riflesso_4_registered.tif (RGB, nativo, lossless)
- Diagnostica: output/registration/step3_export/

L'originale resta intatto. Per installare le librerie:
    python -m pip install opencv-python numpy tifffile

USO: python registration_step3.py
"""

from pathlib import Path
import csv
import gc
import json
import math

import cv2
import numpy as np
import tifffile

# ======================================================
# BLOCCO 1 — Percorsi dei file, relativi a questo script
# ======================================================
ROOT = Path(__file__).resolve().parent
DIR_IMAGES = ROOT / "images"
DIR_PARAMS = ROOT / "output" / "registration" / "step2_rotazione"
DIR_TIFF = ROOT / "output" / "registered"
DIR_CHECK = ROOT / "output" / "registration" / "step3_export"

BASE = DIR_IMAGES / "Base.tif"
MOVING = DIR_IMAGES / "Riflesso_4.tif"
PARAMS = DIR_PARAMS / "04_trasformazioni.json"
DEST = DIR_TIFF / "Riflesso_4_registered.tif"
MASK_DEST = DIR_CHECK / "02_maschera_pixel_validi.png"

# Centri delle zone: frazioni della risoluzione completa.
# Due zone della tavola + quattro del violino.
LATO = 640  # Pixel nativi dei ritagli (nessun resize per le misure).
ZONE = {
    "tavola_sx": (0.32, 0.915),
    "tavola_dx": (0.69, 0.915),
    "alto_sx": (0.30, 0.17),
    "centro_sx": (0.35, 0.43),
    "centro_dx": (0.65, 0.43),
    "basso_dx": (0.68, 0.70),
}


def leggi_matrice_phase(percorso):
    """Recupera la matrice Base -> Riflesso creata e confrontata nello Step 2.

    Attenzione: nella convenzione di ECC/Phase del nostro progetto,
    W descrive dove trovare, nel Riflesso, il pixel di coordinate (x,y)
    della Base. Con cv2.WARP_INVERSE_MAP possiamo usarla DIRETTAMENTE.
    """
    if not percorso.is_file():
        raise FileNotFoundError(
            f"Non trovo {percorso}. Esegui prima registration_step2.py."
        )
    data = json.loads(percorso.read_text(encoding="utf-8"))
    W = np.asarray(data["matrici_base_verso_riflesso"]["Phase"], dtype=np.float32)
    if W.shape != (2, 3) or not np.isfinite(W).all():
        raise ValueError("Matrice Phase non valida: deve essere 2x3, con valori finiti.")
    if not np.allclose(W[:, :2], np.eye(2), atol=1e-6):
        raise ValueError("La matrice Phase non e' una semplice traslazione: fermo l'export.")
    dx, dy = map(float, W[:, 2])
    if math.hypot(dx, dy) > 50:
        raise ValueError("Traslazione superiore a 50 px: controllare i dati prima di procedere.")
    phase = data.get("phase_dxdy", {})
    if abs(dx - float(phase.get("dx", dx))) > 0.02 or abs(dy - float(phase.get("dy", dy))) > 0.02:
        raise ValueError("Matrice Phase e dx/dy nel JSON non sono coerenti.")
    return W, dx, dy


def leggi_rgb_originale(percorso):
    """Legge TUTTI i pixel RGB, senza ridimensionare o convertire in grigi.

    OpenCV carica le immagini colorate in ordine BGR: convertiamo in RGB
    per scrivere poi correttamente il TIFF con la libreria tifffile.
    IMREAD_UNCHANGED mantiene la profondita' numerica originale (8/16 bit).
    """
    imm = cv2.imread(str(percorso), cv2.IMREAD_UNCHANGED)
    if imm is None:
        raise FileNotFoundError(f"Impossibile leggere {percorso}")
    if imm.ndim != 3 or imm.shape[2] != 3 or imm.dtype not in (np.uint8, np.uint16):
        raise ValueError(f"Atteso TIFF RGB a 8/16 bit, ricevuto {imm.shape}, {imm.dtype}")
    return cv2.cvtColor(imm, cv2.COLOR_BGR2RGB)


def metadati_tiff(percorso):
    """Recupera eventuale profilo ICC e risoluzione di stampa dal TIFF.

    ICC e' importante per la resa cromatica in un programma come Paint.NET.
    Non promettiamo di mantenere OGNI tag proprietario o tutti i metadati.
    """
    with tifffile.TiffFile(percorso) as tiff:
        pagina = tiff.pages[0]
        tag_icc = pagina.tags.get(34675)  # tag TIFF InterColorProfile
        icc = bytes(tag_icc.value) if tag_icc is not None else None
        tag_x = pagina.tags.get("XResolution")
        tag_y = pagina.tags.get("YResolution")
        tag_unit = pagina.tags.get("ResolutionUnit")

        def numero(tag):
            if tag is None:
                return None
            v = tag.value
            return float(v[0]) / float(v[1]) if isinstance(v, tuple) else float(v)

        resol = (numero(tag_x), numero(tag_y))
        if None in resol:
            resol = None
        unit = int(tag_unit.value) if tag_unit is not None else None
        return {"icc": icc, "resolution": resol, "resolutionunit": unit}


def campione_centrato(rgb, centro_rel, lato=LATO):
    """Ritaglio di pixel reali, 640x640, in coordinate assolute dell'immagine."""
    h, w = rgb.shape[:2]
    cx, cy = round(centro_rel[0]*w), round(centro_rel[1]*h)
    x0, y0 = cx-lato//2, cy-lato//2
    if x0 < 0 or y0 < 0 or x0+lato > w or y0+lato > h:
        raise ValueError(f"Ritaglio fuori dall'immagine: {centro_rel}")
    return rgb[y0:y0+lato, x0:x0+lato]


def anteprima_8bit_rgb(imm):
    """Solo PNG di anteprima: riduce la profondita' da 16 a 8 bit, se serve.

    L'output TIFF non passa MAI da questa funzione.
    """
    if imm.dtype == np.uint16:
        return (imm >> 8).astype(np.uint8)
    return imm


def anteprima_intera(rgb, max_lato=1150):
    """Ridimensiona soltanto la visualizzazione per contenere il file PNG."""
    h, w = rgb.shape[:2]
    scala = min(1.0, max_lato / max(h, w))
    nuovo = (max(1, round(w*scala)), max(1, round(h*scala)))
    return cv2.resize(anteprima_8bit_rgb(rgb), nuovo, interpolation=cv2.INTER_AREA)


def grayscale_8bit(rgb):
    """Conversione in grigi SOLO per valutare gli spostamenti geometrici."""
    return cv2.cvtColor(anteprima_8bit_rgb(rgb), cv2.COLOR_RGB2GRAY)


def sobel(grigi):
    """Modulo del gradiente, come negli Step 1–5; dati float32."""
    blur = cv2.GaussianBlur(grigi, (3, 3), 0.5).astype(np.float32)
    dx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(dx, dy)


def phase_sui_ritagli(a, b):
    """Misura residuo di traslazione fra i due ritagli, senza modificarli."""
    aa, bb = sobel(grayscale_8bit(a)), sobel(grayscale_8bit(b))
    h, w = aa.shape
    window = cv2.createHanningWindow((w, h), cv2.CV_32F)
    (dx, dy), response = cv2.phaseCorrelate(aa, bb, window)
    return float(dx), float(dy), float(response)


def pannello_rgb(rgb, titolo):
    """Disegna il titolo al di FUORI dei pixel del ritaglio."""
    rgb8 = anteprima_8bit_rgb(rgb)
    h, w = rgb8.shape[:2]
    canvas = np.full((h+52, w, 3), 24, dtype=np.uint8)
    canvas[52:] = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    cv2.putText(canvas, titolo[:80], (12, 33), cv2.FONT_HERSHEY_SIMPLEX,
                0.62, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def overlay_grigi(a, b):
    """Rosso = Base, Ciano = Riflesso (OpenCV salva PNG in ordine BGR)."""
    ga, gb = grayscale_8bit(a), grayscale_8bit(b)
    return cv2.merge([gb, gb, ga])


def pannello_bgr(imm, titolo):
    h, w = imm.shape[:2]
    canvas = np.full((h+52, w, 3), 24, dtype=np.uint8)
    canvas[52:] = imm
    cv2.putText(canvas, titolo[:90], (12, 33), cv2.FONT_HERSHEY_SIMPLEX,
                0.57, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def salva_png(path, array):
    if not cv2.imwrite(str(path), array):
        raise IOError(f"Salvataggio PNG fallito: {path}")


def main():
    # ======================================================
    # BLOCCO 2 — Leggiamo e validiamo matrice e TIFF originali
    # ======================================================
    W, dx, dy = leggi_matrice_phase(PARAMS)
    print(f"Traslazione misurata di Riflesso_4 rispetto a Base: dx={dx:+.4f}, dy={dy:+.4f}")
    print(f"Correzione sul contenuto di Riflesso_4: x={-dx:+.4f}, y={-dy:+.4f}")
    if not BASE.is_file() or not MOVING.is_file():
        raise FileNotFoundError("Mancano images/Base.tif o images/Riflesso_4.tif")
    if DEST.resolve() in (BASE.resolve(), MOVING.resolve()):
        raise RuntimeError("Per sicurezza NON e' possibile sovrascrivere gli originali.")

    # Esaminiamo la geometria e profondita' del TIFF Base senza caricarlo ora.
    with tifffile.TiffFile(BASE) as tf:
        base_shape = tf.series[0].shape
        base_dtype = tf.series[0].dtype
    moving_rgb = leggi_rgb_originale(MOVING)
    if tuple(moving_rgb.shape) != tuple(base_shape) or moving_rgb.dtype != base_dtype:
        raise ValueError(f"Base e Riflesso_4 diversi: Base {base_shape} {base_dtype} | "
                         f"Riflesso_4 {moving_rgb.shape} {moving_rgb.dtype}")
    height, width = moving_rgb.shape[:2]
    print(f"Originale RGB: {width} x {height}, {moving_rgb.dtype} per canale")

    # Blocchiamo la scrittura se il file destinazione esiste gia'.
    # La prima esecuzione quindi non puo' sovrascrivere un risultato precedente.
    if DEST.exists():
        raise FileExistsError(f"Il TIFF registrato esiste gia': {DEST}\n"
                              "Rinominalo/spostalo dopo averlo esaminato, poi riesegui.")

    DIR_TIFF.mkdir(parents=True, exist_ok=True)
    DIR_CHECK.mkdir(parents=True, exist_ok=True)
    md = metadati_tiff(MOVING)
    print('Profilo ICC presente:', bool(md['icc']))

    # Salviamo pochi ritagli e una miniatura PRIMA di liberare l'originale.
    crops_originali = {nome: campione_centrato(moving_rgb, pos).copy()
                       for nome, pos in ZONE.items()}
    mini_orig = anteprima_intera(moving_rgb)

    # ======================================================
    # BLOCCO 3 — UNA SOLA interpolazione sulla foto COLORI completa
    # ======================================================
    # W mappa una coordinata di BASE alla posizione da prelevare in RIFLESSO.
    # Con WARP_INVERSE_MAP OpenCV usa esattamente questa mappatura,
    # anziche' invertire automaticamente la matrice.
    # INTER_LINEAR interpola quando il punto di prelievo cade tra pixel.
    # NON cambiamo dimensioni, gamma, colori o profondita' numerica.
    registrata = cv2.warpAffine(
        moving_rgb, W, (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
    )
    if registrata.shape != moving_rgb.shape or registrata.dtype != moving_rgb.dtype:
        raise AssertionError('Output della registrazione con dimensioni o dtype diversi')

    # Nelle strisce piu' esterne la sorgente non contiene dati.
    # Salviamo quindi una maschera che indica i pixel completamente validi.
    # Valori 255=interamente derivati dalla sorgente; 0=nessun dato sorgente.
    coverage = cv2.warpAffine(
        np.full((height, width), 255, dtype=np.uint8), W, (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    salva_png(MASK_DEST, coverage)

    # ======================================================
    # BLOCCO 4 — Salvataggio TIFF lossless e profilo ICC se presente
    # ======================================================
    # 'compression=None': TIFF non compresso, NESSUNA perdita da JPEG.
    # Il profilo ICC (se esiste nel sorgente) viene copiato nel nuovo TIFF.
    # Il salvataggio mantiene la stessa profondita' di pixel originali.
    tifffile.imwrite(
        DEST, registrata,
        photometric='rgb', metadata=None, compression=None,
        iccprofile=md['icc'],
        resolution=md['resolution'], resolutionunit=md['resolutionunit'],
        software='ViolinReflectionRemoval registration Step 3 / OpenCV phase translation'
    )

    # Rilettura dei soli metadati di output, per verificare quanto scritto.
    with tifffile.TiffFile(DEST) as tf:
        pagina = tf.pages[0]
        actual_shape, actual_dtype = tf.series[0].shape, tf.series[0].dtype
        dst_icc = pagina.tags.get(34675)  # InterColorProfile
        if actual_shape != registrata.shape or actual_dtype != registrata.dtype:
            raise AssertionError('TIFF scritto ma forma/dtype NON corrispondono!')
        if md['icc'] is not None and (dst_icc is None or bytes(dst_icc.value) != md['icc']):
            raise AssertionError('ICC presente nel sorgente, ma assente/diverso nel risultato')
    print(f"TIFF lossless salvato: {DEST}")

    # Possiamo ora liberare il frame sorgente grande: restano i crop di verifica.
    del moving_rgb
    gc.collect()

    # ======================================================
    # BLOCCO 5 — PNG diagnostici a colori + overlay prima/dopo
    # ======================================================
    base_rgb = leggi_rgb_originale(BASE)
    mini_base = anteprima_intera(base_rgb)
    mini_reg = anteprima_intera(registrata)
    pannelli_interi = []
    for label, mini in [('BASE', mini_base), ('RIFLESSO 4 ORIGINALE', mini_orig),
                        ('RIFLESSO 4 REGISTRATO', mini_reg)]:
        p = pannello_rgb(mini, label)
        pannelli_interi.append(p)
    salva_png(DIR_CHECK / '01_anteprima_intera.png', cv2.hconcat(pannelli_interi))

    griglia_colore, griglia_overlay, righe_csv = [], [], []
    for nome, pos in ZONE.items():
        b = campione_centrato(base_rgb, pos)
        o = crops_originali[nome]
        r = campione_centrato(registrata, pos)
        prima = phase_sui_ritagli(b, o)
        dopo = phase_sui_ritagli(b, r)
        tipo = 'calibrazione' if nome.startswith('tavola') else 'verifica'
        righe_csv.append([nome, tipo, *prima, *dopo])
        print(f"{nome:12s} ({tipo:12s}) | prima=({prima[0]:+.2f},{prima[1]:+.2f}) "
              f"q={prima[2]:.3f}; dopo=({dopo[0]:+.2f},{dopo[1]:+.2f}) q={dopo[2]:.3f}")
        griglia_colore.append(cv2.hconcat([
            pannello_rgb(b, f'{nome} | BASE'),
            pannello_rgb(o, 'ORIGINALE'),
            pannello_rgb(r, 'REGISTRATO'),
        ]))
        griglia_overlay.append(cv2.hconcat([
            pannello_bgr(overlay_grigi(b, o),
                         f'{nome} PRIMA dx={prima[0]:+.2f} dy={prima[1]:+.2f}'),
            pannello_bgr(overlay_grigi(b, r),
                         f'{nome} DOPO dx={dopo[0]:+.2f} dy={dopo[1]:+.2f}'),
        ]))

    salva_png(DIR_CHECK / '03_crop_colori_nativi.png', cv2.vconcat(griglia_colore))
    salva_png(DIR_CHECK / '04_overlay_prima_dopo.png', cv2.vconcat(griglia_overlay))
    with (DIR_CHECK / '05_residui.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['zona', 'tipo', 'dx_originale', 'dy_originale', 'risposta_originale',
                         'dx_registrato', 'dy_registrato', 'risposta_registrato'])
        writer.writerows(righe_csv)

    report = {
        'sorgente': str(MOVING.relative_to(ROOT)),
        'riferimento': str(BASE.relative_to(ROOT)),
        'modello': 'PHASE / sola traslazione',
        'dx_riflesso_rispetto_base': dx,
        'dy_riflesso_rispetto_base': dy,
        'correzione_traslazione_x': -dx,
        'correzione_traslazione_y': -dy,
        'matrice_base_verso_riflesso': W.tolist(),
        'risoluzione': [width, height],
        'dtype': str(registrata.dtype),
        'canali': 3,
        'interpolazione': 'cv2.INTER_LINEAR, singolo warp su originale',
        'tiff_lossless': True,
        'icc_profilo_copiato': bool(md['icc']),
        'pixel_coverage_piena_percento': round(100*np.count_nonzero(coverage == 255)/coverage.size, 6),
        'pixel_coverage_parziale_percento': round(100*np.count_nonzero((coverage > 0) & (coverage < 255))/coverage.size, 6),
        'pixel_senza_dati_percento': round(100*np.count_nonzero(coverage == 0)/coverage.size, 6),
        'tiff_originali_modificati': False,
        'avvertenza': 'I pixel sui bordi fuori dalla sorgente sono neri; usare maschera. '
                      'Traslazione subpixel comporta inevitabilmente interpolazione. '
                      'Non sono riprodotti necessariamente tutti i metadati non ICC.'
    }
    (DIR_CHECK / '06_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\nSTEP 3 completato. Nessun file in images/ modificato.')
    print('TIFF:', DEST)
    print('Anteprime, maschera e report:', DIR_CHECK)


if __name__ == '__main__':
    main()