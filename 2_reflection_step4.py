"""FASE 2 / TEST 04 — Fusione selettiva protetta, evoluzione del Test 02.

Nella radice del progetto locale:
    python 2_reflection_step4.py

Richiede 2_reflection_step2.py, Base.tif, i 4 TIFF registrati,
le 4 maschere di validita' della Fase 1 e il TIFF del Test 02.

Non sovrascrive sorgenti, Test 02 o Test 03. Produce un nuovo TIFF
5504x8256 (dimensione nativa), confronto e diagnostiche leggere.

Metodo: riutilizza i guadagni, i donatori e la fusione del Test 02;
protegge le parti non in legno con una maschera cromatica a doppia scala,
e incrementa moderatamente la forza solo dove esiste gia' un candidato
fotometrico credibile. Non promette una separazione fisica dei riflessi.

Dipendenze: numpy, opencv-python, tifffile. Per TIFF LZW compressi
potrebbe essere necessario imagecodecs; OpenCV e' il fallback.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import tifffile

SCALE = 8
STRIPE_ROWS = 320
ALPHA_MULTIPLIER = 1.35
ALPHA_LIMIT = 0.72
DARKEN_LIMIT = 55.0
BRIGHTEN_LIMIT = 20.0


def load_step2(root: Path):
    path = root / '2_reflection_step2.py'
    if not path.is_file():
        raise FileNotFoundError(f'Serve lo script Test 02 in {path}')
    spec = importlib.util.spec_from_file_location('violin_step02_for_step04', path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Impossibile importare {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wood_pixels(rgb8: np.ndarray) -> np.ndarray:
    """Vernice arancio/marrone; esclude corde, ponticello e hardware grigio/nero.

    Sono regole specifiche del dataset, non una segmentazione universale.
    Le zone speculari del tutto bianche possono rimanere escluse.
    """
    hsv = cv2.cvtColor(rgb8, cv2.COLOR_RGB2HSV)
    r = rgb8[:, :, 0].astype(np.float32)
    g = rgb8[:, :, 1].astype(np.float32)
    b = rgb8[:, :, 2].astype(np.float32)
    return ((hsv[:, :, 0] >= 2) & (hsv[:, :, 0] <= 29) &
            (hsv[:, :, 1] >= 68) & (hsv[:, :, 2] >= 45) &
            (r > 1.10 * g) & (g > 1.025 * b))


def wood_confidence(base_preview: np.ndarray, violin_outline: np.ndarray) -> np.ndarray:
    """ROI a bassa scala per continuita'; la selezione nativa resta vincolante."""
    rgb = wood_pixels(base_preview).astype(np.uint8)
    # Colma solo piccoli buchi nell'area del legno, non corde o cordiera.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    rgb = cv2.morphologyEx(rgb, cv2.MORPH_CLOSE, k)
    conf = cv2.GaussianBlur(rgb.astype(np.float32), (0, 0), 1.2)
    return np.clip(conf * violin_outline, 0.0, 1.0)


def apply_native_wood_gate(base_rgb: np.ndarray) -> np.ndarray:
    """Per-pixel in fullres; niente fusioni su corde, ponticello e cordiera."""
    rgb8 = base_rgb if base_rgb.dtype == np.uint8 else (base_rgb >> 8).astype(np.uint8)
    raw = wood_pixels(rgb8)
    # Riflessi moderatamente sbiancati sul legno sono ammessi; non si
    # colmano regioni bianco/grigie senza prova fotografica attendibile.
    return raw.astype(np.float32)


def save_png(path: Path, bgr: np.ndarray) -> None:
    if not cv2.imwrite(str(path), bgr):
        raise OSError(f'Non riesco a salvare {path}')


def run(root: Path, out: Path, preview_width: int = 700) -> None:
    step2 = load_step2(root)
    base_path, donor_paths, mask_paths = step2.percorsi(root)
    previous = root / 'output/02_analisi_riflessi/test_02/01_correzione_globale.tif'
    required = [base_path, *donor_paths, *mask_paths, previous]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError('File locali mancanti:\n' + '\n'.join(map(str, missing)))
    if out == root or out == root / 'images' or root / 'images' in out.parents:
        raise ValueError('Output non consentito nella radice o in images/.')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Cartella di destinazione non vuota: {out}')

    base = step2.apri_rgb(base_path)
    donors = [step2.apri_rgb(p) for p in donor_paths]
    prior = step2.apri_rgb(previous)
    if base.ndim != 3 or base.shape[2] != 3 or base.dtype not in (np.uint8, np.uint16):
        raise ValueError('Base deve essere un TIFF RGB uint8 o uint16.')
    if any(p.shape != base.shape or p.dtype != base.dtype for p in [*donors, prior]):
        raise ValueError('Dimensioni e dtype devono essere uguali tra tutti i TIFF.')
    h, w, _ = base.shape
    masks = []
    for path in mask_paths:
        valid = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if valid is None or valid.shape != (h, w):
            raise ValueError(f'Maschera di validita non valida: {path}')
        masks.append(valid)

    sw = max(1, round(w / SCALE))
    sh = max(1, round(h / SCALE))
    b8 = step2.anteprima(base, sw, sh)
    d8 = [step2.anteprima(d, sw, sh) for d in donors]
    masks8 = [cv2.resize(m, (sw, sh), interpolation=cv2.INTER_NEAREST) for m in masks]

    print('Calcolo delle mappe originali del Test 02...')
    old_alpha, weights, gains, outline = step2.calcola_mappe(b8, d8, masks8)
    wood = wood_confidence(b8, outline)
    # Mantenere Base intatta dove non esiste un candidato dal Test 02;
    # non inventare nuovi dettagli. La maggiore forza e' moderata.
    new_alpha = np.clip(old_alpha * ALPHA_MULTIPLIER * wood, 0, ALPHA_LIMIT)
    new_alpha[new_alpha < 0.018] = 0.0

    out.mkdir(parents=True, exist_ok=True)
    result_path = out / '01_correzione_protetta.tif'
    icc = step2.icc_originale(base_path)
    extratags = [(34675, 'B', len(icc), icc, False)] if icc else None
    writer = tifffile.memmap(result_path, shape=base.shape, dtype=base.dtype,
                             photometric='rgb', metadata=None, extratags=extratags)
    scale = float(np.iinfo(base.dtype).max) / 255.0
    count = 0
    count_affected = 0
    sum_difference = 0.0
    print('Fusione a risoluzione nativa con protezione del legno...')
    for y0 in range(0, h, STRIPE_ROWS):
        y1 = min(h, y0 + STRIPE_ROWS)
        original_rgb = base[y0:y1]
        origin = original_rgb.astype(np.float32) / scale
        alpha = step2.scala_striscia(new_alpha, y0, y1, h, w)
        alpha *= apply_native_wood_gate(original_rgb)
        corrected = origin.copy()
        for i, donor in enumerate(donors):
            quota = alpha * step2.scala_striscia(weights[i], y0, y1, h, w)
            quota *= (masks[i][y0:y1] > 0)
            if not np.any(quota > 0.002):
                continue
            gain = step2.scala_striscia(gains[i], y0, y1, h, w)
            donor_normalized = donor[y0:y1].astype(np.float32) / scale * gain
            delta = np.clip(donor_normalized - origin, -DARKEN_LIMIT, BRIGHTEN_LIMIT)
            corrected += quota[:, :, None] * delta
        new_slice = np.rint(np.clip(corrected * scale, 0, np.iinfo(base.dtype).max)).astype(base.dtype)
        writer[y0:y1] = new_slice
        difference = np.max(np.abs(new_slice.astype(np.float32) - original_rgb.astype(np.float32)), axis=2) / scale
        count += int(np.count_nonzero(difference >= 1.0))
        difference_prior = np.max(np.abs(new_slice.astype(np.float32) - prior[y0:y1].astype(np.float32)), axis=2) / scale
        count_affected += int(np.count_nonzero(difference_prior >= 1.0))
        sum_difference += float(difference_prior.sum(dtype=np.float64))
        if y0 == 0 or y1 == h or (y0 // STRIPE_ROWS) % 8 == 0:
            print(f'  {y1}/{h} righe')
    writer.flush()
    del writer

    # Solo anteprime e mappe vengono ridotte: il TIFF e' full resolution.
    pw = min(w, preview_width)
    ph = max(1, round(h * pw / w))
    after = step2.apri_rgb(result_path)
    panels = [step2.anteprima(x, pw, ph) for x in [base, prior, after]]
    joined = cv2.hconcat(panels)
    for i, label in enumerate(('BASE', 'TEST 02', 'TEST 04')):
        cv2.putText(joined, label, (i * pw + 12, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    .75, (255, 255, 255), 2, cv2.LINE_AA)
    save_png(out / '02_base_test02_test04.png', cv2.cvtColor(joined, cv2.COLOR_RGB2BGR))

    colormap = cv2.resize(new_alpha, (pw, ph), interpolation=cv2.INTER_LINEAR)
    cmap = cv2.applyColorMap(np.clip(colormap / ALPHA_LIMIT * 255, 0, 255).astype(np.uint8),
                            cv2.COLORMAP_VIRIDIS)
    save_png(out / '03_mappa_intervento.png', cmap)
    grayscale = cv2.resize(wood, (pw, ph), interpolation=cv2.INTER_LINEAR)
    save_png(out / '04_maschera_legno.png', np.clip(grayscale * 255, 0, 255).astype(np.uint8))

    report = f'''# Fase 2 / Test 04 — Fusione protetta

- Dimensione: {w} × {h} px, {base.dtype}; elaborazione alla risoluzione originale.
- Algoritmo: pesi e normalizzazione del Test 02, maschera cromatica del legno a doppia scala.
- Alpha moltiplicato per {ALPHA_MULTIPLIER:.2f}, massimo {ALPHA_LIMIT:.2f}; limiti delta RGB [{-DARKEN_LIMIT:.0f}, +{BRIGHTEN_LIMIT:.0f}]/255.
- Pixel modificati rispetto a Base (≥1/255): {count:,} ({100*count/(h*w):.2f}%).
- Pixel diversi dal Test 02 (≥1/255): {count_affected:,} ({100*count_affected/(h*w):.2f}%).
- Differenza media massima per pixel rispetto al Test 02: {sum_difference/(h*w):.3f}/255.

## Interpretazione

Verificare la macchia principale, i bordi e i dettagli sul TIFF al 100%.
La maschera esclude le zone non riconosciute come legno: riflessi molto
bianchi/azzurri sui bordi potrebbero restare. Non confondere la riduzione
di luminosita con la rimozione del riflesso.

Nessun originale e nessun risultato precedente modificato.
'''
    (out / 'osservazioni.md').write_text(report, encoding='utf-8')
    print('Risultato:', result_path)
    print('Anteprima:', out / '02_base_test02_test04.png')


def main():
    parser = argparse.ArgumentParser(description='Test 04 — Fusione selettiva protetta')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--preview-width', type=int, default=700)
    args = parser.parse_args()
    if not 250 <= args.preview_width <= 1400:
        parser.error('--preview-width deve essere tra 250 e 1400')
    root = args.root.resolve()
    out = (args.out or root / 'output/02_analisi_riflessi/test_04').resolve()
    run(root, out, args.preview_width)


if __name__ == '__main__':
    main()