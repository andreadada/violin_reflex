"""FASE 1 — Image Registration delle quattro fotografie del violino.

USO (dalla radice del progetto):
    python code/phase1_registration/registration_pipeline.py
    python code/phase1_registration/registration_pipeline.py --dry-run
    python code/phase1_registration/registration_pipeline.py --root F:\\intelliJProjects\\ViolinReflectionRemoval

Dipendenze: opencv-python, numpy, tifffile.
Non modifica mai images/. Lavora su pixel a risoluzione originale. Le immagini
in scala di grigi servono SOLO per stimare/verificare la geometria. Il warp
finale (se accettato) viene fatto UNA volta sul TIFF RGB originale.

Strategia prudente (coerente con gli esperimenti precedenti):
  1. Base.tif resta il riferimento immobile.
  2. Phase Correlation/Sobel sulle DUE zone della tavola colori: stima dx,dy.
  3. Correzioni <1.5 px: immagini lasciate IDENTICHE agli originali.
  4. Correzioni >=1.5 px: test su TRE/QUATTRO aree indipendenti del violino.
  5. Si applica la correzione solo se almeno 2 zone e metriche concordano.
  6. Un risultato incerto viene conservato, ma MARCATO 'REVIEW_UNCHANGED'.

Gli indicatori di correlazione non sono probabilita' di correttezza. Una
registrazione puo' essere geometricamente corretta e avere differenze rosso/
ciano dovute alle diverse illuminazioni.


SCHEDA DEL FILE (riferita al progetto locale)
Obiettivo: Consolidare la registrazione geometrica prudente dei quattro scatti rispetto a Base.
Input: Cinque TIFF originali in images/.
Output: TIFF registrati/invariati, maschere valide e report in output/01_registrazione/test_01/.
Fasi: Phase Correlation su Sobel nella tavola colori; verifica sul violino; singolo warp solo quando giustificato.
Risultato atteso: Quattro immagini utilizzabili dalla Fase 2 e una decisione documentata per ogni scatto.
Nota: Pipeline di riferimento: la Fase 1 è già validata, non rieseguirla senza necessità.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import tifffile

# STEP A: regioni relative su ORIGINALI 5504x8256. Le due zone della tavola
# stimano lo spostamento. Le altre sono un test SEPARATO e non ottimizzano dx/dy.
CALIBRAZIONE = {
    "tavola_sx": (0.32, 0.915),
    "tavola_dx": (0.69, 0.915),
}
VERIFICA = {
    "alto_sx": (0.30, 0.17),
    "centro_sx": (0.35, 0.43),
    "centro_dx": (0.65, 0.43),
    "basso_dx": (0.68, 0.70),
}

# Soglie di decisione ERUISTICHE ricavate come prudente scelta operativa,
# non come prova scientifica che 'tutti i pixel sono perfettamente registrati'.
SOGLIA_MAGNITUDINE = 1.5       # Sotto 1.5 px non riscriviamo il TIFF.
SOGLIA_Q_TAVOLA = 0.20         # Qualita' phase, NON probabilita'.
DISACCORDO_TAVOLA_MAX = 2.0    # Le due stime tavola devono concordare entro 2 px.
SOGLIA_Q_VERIFICA = 0.12       # R1-4: superfici del legno spesso poco informative.
MIN_ZONE_VERIFICA = 2
RIDUZIONE_MIN_PX = 1.5       # Il residuo mediano deve calare almeno 1.5 px.
RAPPORTO_MAX_RESIDUI = 0.65   # E diventare <= 65% della misura originale.
GUADAGNO_MIN_CORR = 0.04      # E aumentare correlazione media dei gradienti.
MASSIMA_TRASLAZIONE = 30.0    # Blocca stime assurde da periodicita' / rumore.


def info_tiff(path: Path) -> dict:
    """Ispezione senza caricare in RAM tutti i pixel."""
    with tifffile.TiffFile(path) as tf:
        series = tf.series[0]
        page = tf.pages[0]
        shape, dtype = tuple(series.shape), np.dtype(series.dtype)
        if len(shape) != 3 or shape[-1] != 3 or dtype not in (np.dtype("uint8"), np.dtype("uint16")):
            raise ValueError(f"Atteso TIFF RGB uint8/uint16: {path.name}: {shape}, {dtype}")
        tag_icc = page.tags.get(34675)  # InterColorProfile / ICC
        icc = bytes(tag_icc.value) if tag_icc is not None else None
        tx = page.tags.get("XResolution")
        ty = page.tags.get("YResolution")
        tu = page.tags.get("ResolutionUnit")

        def ratio(t):
            if t is None:
                return None
            val = t.value
            return (float(val[0]) / float(val[1])) if isinstance(val, tuple) else float(val)

        res = (ratio(tx), ratio(ty))
        if None in res:
            res = None
        return {"shape": shape, "dtype": dtype, "icc": icc,
                "resolution": res, "unit": int(tu.value) if tu is not None else None}


def load_gray(path: Path, expected_shape: tuple[int, int]) -> np.ndarray:
    """Grigio a pixel NATIVI. Conversione a 8 bit solo per la stima geometrica."""
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None or image.shape != expected_shape:
        raise ValueError(f"Lettura grigio fallita o dimensioni diverse: {path}")
    return image


def load_rgb(path: Path, expected_shape: tuple[int, int, int], dtype: np.dtype) -> np.ndarray:
    """Lettura del vero RGB senza ridimensionamento e senza cambiare bit-depth."""
    image_bgr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image_bgr is None or image_bgr.shape != expected_shape or image_bgr.dtype != dtype:
        raise ValueError(f"RGB non corrispondente al riferimento: {path}")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def crop(gray: np.ndarray, position: tuple[float, float], size: int) -> np.ndarray:
    """Estrae una ROI centrata sulle coordinate relative, senza ridurre i pixel."""
    h, w = gray.shape[:2]
    xc, yc = round(position[0] * w), round(position[1] * h)
    x0, y0 = xc - size // 2, yc - size // 2
    if x0 < 0 or y0 < 0 or x0 + size > w or y0 + size > h:
        raise ValueError(f"Crop di {size}px oltre i confini: {position}, dimensioni {w}x{h}")
    return gray[y0:y0+size, x0:x0+size]


def sobel(gray: np.ndarray) -> np.ndarray:
    """Gradienti Sobel float32, con lieve filtro gaussiano solo diagnostico."""
    f = cv2.GaussianBlur(gray, (3, 3), 0.5).astype(np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def phase(gray_a: np.ndarray, gray_b: np.ndarray) -> tuple[float, float, float]:
    """Misura spostamento di B RISPETTO ad A; e' su immagini NON modificate."""
    ga, gb = sobel(gray_a), sobel(gray_b)
    win = cv2.createHanningWindow((ga.shape[1], ga.shape[0]), cv2.CV_32F)
    (dx, dy), q = cv2.phaseCorrelate(ga, gb, win)
    return float(dx), float(dy), float(q)


def gradient_corr(gray_a: np.ndarray, gray_b: np.ndarray, margin: int = 24) -> float:
    """Correlazione Pearson dei moduli Sobel (non equivale ad accuratezza)."""
    a, b = sobel(gray_a), sobel(gray_b)
    if min(a.shape) <= 2 * margin:
        margin = 0
    if margin:
        a, b = a[margin:-margin, margin:-margin], b[margin:-margin, margin:-margin]
    a = a.ravel().astype(np.float64)
    b = b.ravel().astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    den = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / den) if den > 1e-12 else 0.0


def aligned_crop(moving: np.ndarray, position: tuple[float,float], size: int,
                 dx: float, dy: float, margin: int = 48) -> np.ndarray:
    """Crop corretto IN MODO INDIPENDENTE, con margine dalla foto nativa.

    La foto B si trova a (+dx,+dy) rispetto a Base. Con WARP_INVERSE_MAP
    campioniamo il pixel sorgente in (x+dx,y+dy); NON accumuliamo interpolazioni.
    Questa e' soltanto una simulazione sui crop per decidere la registrazione.
    """
    h, w = moving.shape[:2]
    xc, yc = round(position[0] * w), round(position[1] * h)
    x0, y0 = xc - size // 2, yc - size // 2
    xe, ye = x0 - margin, y0 - margin
    s = size + 2 * margin
    if min(xe, ye) < 0 or xe + s > w or ye + s > h:
        raise ValueError("Margine extra della verifica fuori dai confini")
    extra = moving[ye:ye+s, xe:xe+s]
    Wlocal = np.array([[1., 0., margin + dx], [0., 1., margin + dy]], np.float32)
    return cv2.warpAffine(extra, Wlocal, (size, size),
                          flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def phase_on_chart(base: np.ndarray, moving: np.ndarray, size: int) -> tuple[dict, tuple | None, str]:
    """Stima la traslazione su due zone della tavola colori e verifica che concordino."""
    measures: dict[str, dict] = {}
    accepted = []
    for name, pos in CALIBRAZIONE.items():
        dx, dy, q = phase(crop(base, pos, size), crop(moving, pos, size))
        measures[name] = {"dx": dx, "dy": dy, "q": q}
        if np.isfinite([dx, dy, q]).all() and q >= SOGLIA_Q_TAVOLA:
            accepted.append((dx, dy))
    if len(accepted) != 2:
        return measures, None, "misure della tavola insufficienti"
    if np.linalg.norm(np.subtract(accepted[0], accepted[1])) > DISACCORDO_TAVOLA_MAX:
        return measures, None, "le due zone della tavola non concordano"
    dx, dy = np.median(np.array(accepted, dtype=np.float64), axis=0)
    if math.hypot(dx, dy) > MASSIMA_TRASLAZIONE:
        return measures, None, "spostamento superiore al limite di sicurezza"
    return measures, (float(dx), float(dy)), "due zone tavola concordanti"


def verify_on_violin(base: np.ndarray, moving: np.ndarray, size: int,
                     dx: float, dy: float) -> tuple[list[dict], dict]:
    """Confronto sui contorni nelle zone NON usate per stimare la traslazione."""
    rows = []
    ok = []
    for name, pos in VERIFICA.items():
        a = crop(base, pos, size)
        b = crop(moving, pos, size)
        corrected = aligned_crop(moving, pos, size, dx, dy)
        old_dx, old_dy, old_q = phase(a, b)
        new_dx, new_dy, new_q = phase(a, corrected)
        old_corr, new_corr = gradient_corr(a, b), gradient_corr(a, corrected)
        reliable = (np.isfinite([old_dx, old_dy, old_q, new_dx, new_dy, new_q]).all()
                    and min(old_q, new_q) >= SOGLIA_Q_VERIFICA
                    and math.hypot(old_dx, old_dy) < MASSIMA_TRASLAZIONE + 10
                    and math.hypot(new_dx, new_dy) < MASSIMA_TRASLAZIONE + 10)
        row = dict(zona=name, q_prima=old_q, q_dopo=new_q,
                   dx_prima=old_dx, dy_prima=old_dy,
                   dx_dopo=new_dx, dy_dopo=new_dy,
                   corr_prima=old_corr, corr_dopo=new_corr, valida=bool(reliable))
        rows.append(row)
        if reliable:
            ok.append(row)
    if len(ok) < MIN_ZONE_VERIFICA:
        return rows, {"valid_regions": len(ok), "passed": False,
                      "reason": "meno di due regioni indipendenti affidabili"}
    before = float(np.median([math.hypot(r['dx_prima'], r['dy_prima']) for r in ok]))
    after = float(np.median([math.hypot(r['dx_dopo'], r['dy_dopo']) for r in ok]))
    corr_before = float(np.mean([r['corr_prima'] for r in ok]))
    corr_after = float(np.mean([r['corr_dopo'] for r in ok]))
    passed = (before - after >= RIDUZIONE_MIN_PX
              and after <= before * RAPPORTO_MAX_RESIDUI
              and corr_after - corr_before >= GUADAGNO_MIN_CORR)
    metrics = dict(valid_regions=len(ok), residuo_mediano_prima_px=before,
                   residuo_mediano_dopo_px=after,
                   corr_media_prima=corr_before, corr_media_dopo=corr_after,
                   passed=bool(passed),
                   reason="miglioramento indipendente confermato" if passed
                          else "miglioramento insufficiente o contraddittorio")
    return rows, metrics


def valid_mask(height: int, width: int, dx: float, dy: float) -> np.ndarray:
    """255 = ogni campione bilineare ha dati sorgente, 0 = altrimenti.

    Il campionamento inverse map usa x_s=x+dx, y_s=y+dy. La convoluzione
    bilineare utilizza floor/ceil del punto sorgente. Margine 0/1 netto:
    i pixel parziali sono esclusi dalla maschera di fusione.
    """
    xx = np.arange(width, dtype=np.float64) + dx
    yy = np.arange(height, dtype=np.float64) + dy
    valid_x = (np.floor(xx) >= 0) & (np.ceil(xx) < width)
    valid_y = (np.floor(yy) >= 0) & (np.ceil(yy) < height)
    return (valid_y[:, None] & valid_x[None, :]).astype(np.uint8) * 255


def save_warped_tiff(src: Path, dst: Path, inf: dict, W: np.ndarray) -> None:
    """UNA sola interpolazione sull'RGB originale (8 o 16 bit); TIFF lossless."""
    rgb = load_rgb(src, inf['shape'], inf['dtype'])
    height, width = rgb.shape[:2]
    registered = cv2.warpAffine(
        rgb, W, (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
    )
    if registered.shape != rgb.shape or registered.dtype != rgb.dtype:
        raise AssertionError("warpAffine ha cambiato forma o profondita' colore")
    # File temporaneo su disco e rename: un crash non lascia TIFF finale troncato.
    temp = dst.with_name(dst.stem + '.writing.tif')
    try:
        tifffile.imwrite(temp, registered, photometric='rgb', metadata=None,
                         compression=None, iccprofile=inf['icc'],
                         resolution=inf['resolution'], resolutionunit=inf['unit'],
                         software='ViolinRegistration phase automated pipeline')
        with tifffile.TiffFile(temp) as tf:
            out_shape, out_dtype = tuple(tf.series[0].shape), np.dtype(tf.series[0].dtype)
            icc_tag = tf.pages[0].tags.get(34675)
            if out_shape != inf['shape'] or out_dtype != inf['dtype']:
                raise AssertionError('Verifica output: shape/dtype errati')
            if inf['icc'] is not None and (icc_tag is None or bytes(icc_tag.value) != inf['icc']):
                raise AssertionError('Il profilo ICC non e\' stato preservato')
        if dst.exists():
            raise FileExistsError(f"Output gia' presente: {dst}")
        os.rename(temp, dst)  # NON sovrascrive un file finale gia' presente (precheck).
    finally:
        if temp.exists():
            temp.unlink()


def photo_preview(path: Path, max_height: int = 750) -> np.ndarray:
    """Solo VISUALIZZAZIONE: RGB -> BGR8, ridimensionamento dell'anteprima."""
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Impossibile leggere foto per anteprima: {path}")
    if image.dtype == np.uint16:
        image = (image >> 8).astype(np.uint8)
    h, w = image.shape[:2]
    f = min(1.0, max_height / h)
    return cv2.resize(image, (max(1, round(w*f)), max(1, round(h*f))), interpolation=cv2.INTER_AREA)


def panel(image: np.ndarray, title: str, description: str = '', width: int = 340) -> np.ndarray:
    """Stessa dimensione per confronti 4 colonne. Titolo fuori dall'immagine."""
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image
    hh, ww = image.shape[:2]
    h_image = 490
    factor = min(width/ww, h_image/hh)
    size = (max(1, round(ww*factor)), max(1, round(hh*factor)))
    image_small = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    canvas = np.full((h_image+72, width, 3), 26, dtype=np.uint8)
    px = (width - size[0])//2
    py = 58 + (h_image - size[1])//2
    canvas[py:py+size[1], px:px+size[0]] = image_small
    cv2.putText(canvas, title[:32], (8, 25), cv2.FONT_HERSHEY_SIMPLEX,
                0.48, (255,255,255), 1, cv2.LINE_AA)
    if description:
        cv2.putText(canvas, description[:43], (8, 47), cv2.FONT_HERSHEY_SIMPLEX,
                    0.37, (195,195,195), 1, cv2.LINE_AA)
    return canvas


def diagnostic_png(path: Path, base_gray: np.ndarray, moving_gray: np.ndarray,
                   pos: tuple[float,float], size: int, dx: float, dy: float,
                   title: str, applied: bool) -> None:
    """Crea un'immagine diagnostica della registrazione, separata dall'output nativo."""
    a, b = crop(base_gray, pos, size), crop(moving_gray, pos, size)
    # Mostriamo l'output EFFETTIVO, non una correzione candidata poi scartata.
    c = aligned_crop(moving_gray, pos, size, dx, dy) if applied else b.copy()
    # Rosso = Base, ciano = moving (BGR). Le luci possono cambiarne l'aspetto.
    ab = cv2.merge([b,b,a])
    ac = cv2.merge([c,c,a])
    h, w = ab.shape[:2]
    caption = np.full((45,2*w,3),25,np.uint8)
    cv2.putText(caption, f'{title} | PRIMA', (7,28), cv2.FONT_HERSHEY_SIMPLEX,
                0.52,(255,255,255),1,cv2.LINE_AA)
    label = 'DOPO PHASE APPLICATA' if applied else 'OUTPUT INVARIATO'
    cv2.putText(caption, label + ' | R=Base C=Riflesso', (w+7,28),cv2.FONT_HERSHEY_SIMPLEX,
                0.48,(255,255,255),1,cv2.LINE_AA)
    result = cv2.vconcat([caption,cv2.hconcat([ab,ac])])
    if not cv2.imwrite(str(path), result):
        raise IOError(f'PNG non salvato: {path}')


def make_summary_preview(root: Path, output: Path, statuses: list[dict]) -> None:
    """Griglia con confronto visivo di tutte le 4 foto, senza confondere i flag."""
    strips = []
    for s in statuses:
        name = s['foto']
        original = photo_preview(root/'images'/f'{name}.tif')
        registered = photo_preview(output/'registered'/f'{name}_registered.tif')
        status = s['stato']
        strips.append(cv2.hconcat([
            panel(original, f'{name} originale'),
            panel(registered, f'{name} finale',status)
        ]))
    overview = cv2.vconcat(strips)
    path = output/'01_panorama_originali_vs_registrati.png'
    if not cv2.imwrite(str(path), overview):
        raise IOError(f'PNG non salvato: {path}')



def make_overlay_grid(output: Path, statuses: list[dict]) -> None:
    """Una sola griglia: 2 zone x 4 fotografie, PRIMA/OUTPUT reale in overlay.

    PNG individuali: pixel nativi dei crop. Questa griglia: solo anteprima
    ridotta al 50% per facilitare confronto e lettura in Paint.NET/PyCharm.
    """
    rows = []
    for name_suffix in ('tavola_sx', 'centro_sx'):
        panels = []
        for s in statuses:
            file = output/'diagnostics'/f"{s['foto']}_{name_suffix}.png"
            img = cv2.imread(str(file), cv2.IMREAD_COLOR)
            if img is None:
                raise IOError(f'Diagnostica assente: {file}')
            h,w = img.shape[:2]
            panels.append(cv2.resize(img, (w//2,h//2), interpolation=cv2.INTER_AREA))
        rows.append(cv2.hconcat(panels))
    grid = cv2.vconcat(rows)
    header = np.full((60, grid.shape[1], 3),25,np.uint8)
    cv2.putText(header,'OVERLAY - ROSSO: BASE | CIANO: RIFLESSO | RIGA1 TAVOLA, RIGA2 VIOLINO',
                (12,34),cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),1,cv2.LINE_AA)
    result = cv2.vconcat([header,grid])
    file = output/'05_overlay_quattro_foto.png'
    if not cv2.imwrite(str(file), result):
        raise IOError(f'Non riesco a salvare la griglia {file}')


def run(root: Path, output: Path, size: int, dry_run: bool, no_preview: bool) -> dict:
    """Coordina controlli, stima, verifica, eventuale warp e report senza sovrascrivere output esistenti."""
    root, output = root.resolve(), output.resolve()
    images = root / 'images'
    files = [images/f'Riflesso_{i}.tif' for i in range(1,5)]
    base_path = images/'Base.tif'
    if not base_path.is_file() or any(not f.is_file() for f in files):
        raise FileNotFoundError('Servono images/Base.tif e immagini Riflesso_1.tif ... Riflesso_4.tif')
    if output == images or images in output.parents or output == root:
        raise ValueError('Output non deve essere dentro images/ o coincidere con la root')
    # Impediamo un secondo run di sovrascrivere output confermati.
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"La cartella output non e' vuota: {output}. "
                              "Usa un altro --out o sposta prima la vecchia cartella.")
    info = info_tiff(base_path)
    h, w, _ = info['shape']
    for f in files:
        inf = info_tiff(f)
        if inf['shape'] != info['shape'] or inf['dtype'] != info['dtype']:
            raise ValueError(f'{f.name} non ha shape/dtype uguali a Base')
    base_gray = load_gray(base_path, (h, w))
    print(f'Base: {w} x {h}, RGB {info["dtype"]}, verifica geometrica su pixel nativi')
    results, zone_rows = [], []
    if not dry_run:
        (output/'registered').mkdir(parents=True, exist_ok=True)
        (output/'masks').mkdir(parents=True, exist_ok=True)
        (output/'diagnostics').mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(files, 1):
        name = f'Riflesso_{i}'
        moving = load_gray(src, (h, w))
        chart, shift, chart_msg = phase_on_chart(base_gray, moving, size)
        metrics = None
        shift_mag = float(math.hypot(*shift)) if shift is not None else None
        if shift is None:
            status = 'REVIEW_UNCHANGED'
            reason = chart_msg
        elif shift_mag < SOGLIA_MAGNITUDINE:
            status = 'UNCHANGED_SMALL_SHIFT'
            reason = f'correzione non necessaria: spostamento {shift_mag:.3f} px < {SOGLIA_MAGNITUDINE:.1f} px'
        else:
            local, metrics = verify_on_violin(base_gray, moving, size, *shift)
            for row in local:
                zone_rows.append({'foto':name,**row})
            status = 'REGISTERED' if metrics['passed'] else 'REVIEW_UNCHANGED'
            reason = metrics['reason']
        s = dict(foto=name, stato=status, motivo=reason,
                 icc_input_presente=bool(info_tiff(src)['icc']),
                 dx=float(shift[0]) if shift else None,
                 dy=float(shift[1]) if shift else None,
                 modulo_dxdy_px=shift_mag, tavola=chart,
                 verifica_indipendente=metrics)
        results.append(s)
        print(f'{name:12s}: dx={s["dx"] if shift else "?"}, dy={s["dy"] if shift else "?"}, '
              f'-> {status}: {reason}')
        if dry_run:
            continue
        dst = output/'registered'/f'{name}_registered.tif'
        inf = info_tiff(src)
        if status == 'REGISTERED':
            W = np.array([[1,0,shift[0]],[0,1,shift[1]]], dtype=np.float32)
            save_warped_tiff(src, dst, inf, W)
            mask = valid_mask(h, w, *shift)
        else:
            shutil.copy2(src, dst)  # Stessi byte e metadati TIFF originali, nessuna interpolazione.
            mask = np.full((h,w),255,np.uint8)
        mask_path = output/'masks'/f'{name}_valid.png'
        if not cv2.imwrite(str(mask_path),mask):
            raise IOError('Non riesco a salvare la maschera '+str(mask_path))
        s['output_tiff'] = str(dst.relative_to(output))
        s['mask_pixel_validi'] = str(mask_path.relative_to(output))
        s['pixel_validi_percento'] = round(100*np.count_nonzero(mask)/mask.size,6)
        if not no_preview:
            # Se non c'e' stima o la correzione e' scartata, il DOPO
            # deve rappresentare l'immagine realmente esportata: invariata.
            shift_plot = shift if shift is not None else (0.0, 0.0)
            applied = status == 'REGISTERED'
            diagnostic_png(output/'diagnostics'/f'{name}_tavola_sx.png',base_gray,moving,
                           CALIBRAZIONE['tavola_sx'],size,*shift_plot,name,applied)
            diagnostic_png(output/'diagnostics'/f'{name}_centro_sx.png',base_gray,moving,
                           VERIFICA['centro_sx'],size,*shift_plot,name,applied)
        del moving
    report = dict(progetto='ViolinReflectionRemoval — image registration phase',
                  base='images/Base.tif',shape=list(info['shape']),dtype=str(info['dtype']),
                  risoluzione_originale_preservata=True,
                  registrazione_di_piccoli_spostamenti_evitate=True,
                  interpolazione='cv2.INTER_LINEAR + WARP_INVERSE_MAP soltanto se stato REGISTERED',
                  soglie=dict(shift_min_px=SOGLIA_MAGNITUDINE,q_chart_min=SOGLIA_Q_TAVOLA,
                              q_verifica_min=SOGLIA_Q_VERIFICA,regioni_min=MIN_ZONE_VERIFICA,
                              riduzione_min_px=RIDUZIONE_MIN_PX,
                              rapporto_residuo_max=RAPPORTO_MAX_RESIDUI,
                              guadagno_corr_min=GUADAGNO_MIN_CORR),
                  risultati=results)
    if not dry_run:
        with (output/'02_report.json').open('w',encoding='utf-8') as fd:
            json.dump(report,fd,indent=2,ensure_ascii=False)
        with (output/'03_summary.csv').open('w',newline='',encoding='utf-8') as fd:
            writer=csv.writer(fd)
            writer.writerow(['foto','stato','dx','dy','modulo_px','zone_affidabili',
                             'mediana_prima','mediana_dopo','corr_prima','corr_dopo','motivo'])
            for s in results:
                m=s['verifica_indipendente'] or {}
                writer.writerow([s['foto'],s['stato'],s['dx'],s['dy'],s['modulo_dxdy_px'],
                                 m.get('valid_regions'),m.get('residuo_mediano_prima_px'),
                                 m.get('residuo_mediano_dopo_px'),m.get('corr_media_prima'),
                                 m.get('corr_media_dopo'),s['motivo']])
        with (output/'04_zone.csv').open('w',newline='',encoding='utf-8') as fd:
            writer=csv.DictWriter(fd,fieldnames=['foto','zona','q_prima','q_dopo',
                                                   'dx_prima','dy_prima','dx_dopo','dy_dopo',
                                                   'corr_prima','corr_dopo','valida'])
            writer.writeheader()
            writer.writerows(zone_rows)
        if not no_preview:
            make_summary_preview(root,output,results)
            make_overlay_grid(output,results)
    return report


def main() -> None:
    """Legge gli argomenti CLI e avvia la pipeline con la root del progetto corretta."""
    p=argparse.ArgumentParser(description='Consolida Phase Registration sulle 4 immagini TIFF a piena risoluzione')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2],
                   help='Root con images/Base.tif e Riflesso_1..4.tif')
    p.add_argument('--out',type=Path,default=None,help='Cartella output (vuota/nuova)')
    p.add_argument('--crop-size',type=int,default=640,help='Lato ritagli in pixel originali')
    p.add_argument('--dry-run',action='store_true',help='Solo stime, NON produce TIFF/PNG')
    p.add_argument('--no-preview',action='store_true',help='Omette le immagini PNG di confronto')
    args=p.parse_args()
    if args.crop_size < 64 or args.crop_size > 1000:
        p.error('crop-size deve essere tra 64 e 1000 pixel nativi')
    out = args.out if args.out is not None else args.root/'output'/'registration_pipeline'
    report = run(args.root,out,args.crop_size,args.dry_run,args.no_preview)
    if args.dry_run:
        print('\nDRY RUN — nessun file scritto. Riepilogo:')
        for s in report['risultati']:
            print(f"  {s['foto']}: {s['stato']}")
    else:
        print(f'\nFASE 1 completata. Output: {out}')
        print('Attenzione: REVIEW_UNCHANGED indica dati INCERTI, non conferma di allineamento.')


if __name__=='__main__':
    main()