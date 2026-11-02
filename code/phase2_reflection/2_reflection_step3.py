"""FASE 2 / TEST 03 — Valuta la fusione del Test 02 senza modificarla.

Da ViolinReflectionRemoval:
    python code/phase2_reflection/2_reflection_step3.py
    python code/phase2_reflection/2_reflection_step3.py --crop 640

Richiede i cinque TIFF (Base + quattro registrati), le relative maschere di
validita' e output/02_analisi_riflessi/test_02/01_correzione_globale.tif.

Crea confronti a pixel nativi: Base, Test02, donatori originali e donatori
con la normalizzazione lenta di Test02. Nessuna nuova correzione, nessuna
sovrascrittura di risultati precedenti. Il punteggio delle aree e' un'euristica
per scegliere cosa OSSERVARE, non identifica riflessi con certezza.

Dipendenze: numpy, opencv-python, tifffile (imagecodecs per TIFF compressi).


SCHEDA DEL FILE (riferita al progetto locale)
Obiettivo: Analizzare dove la fusione del Test 02 ha funzionato e dove restano riflessi.
Input: Base, donatori registrati, maschere e TIFF corretto del Test 02.
Output: Ritagli comparativi e report in output/02_analisi_riflessi/test_03/.
Fasi: Individuazione euristica delle zone; crop a pixel nativi; confronti di donatori anche normalizzati.
Risultato atteso: Diagnosi dei limiti del Test 02 senza generare un nuovo TIFF corretto.
Nota: La scelta delle zone è euristica: alcuni candidati individuati erano ponticello e cordiera.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import tifffile

SCALE = 8  # solo mappe diagnostiche: i ritagli restano a risoluzione originale


def load_step2(root: Path):
    """Importa le funzioni del Test 02 dalla stessa cartella del codice."""
    path = Path(__file__).resolve().with_name('2_reflection_step2.py')
    if not path.is_file():
        raise FileNotFoundError(f'Non trovo lo script precedente: {path}')
    spec = importlib.util.spec_from_file_location('reflection_phase2_step2', path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Impossibile importare {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gray(rgb: np.ndarray) -> np.ndarray:
    """Converte il RGB in un'immagine monocromatica per le misure."""
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)


def blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Calcola una media spaziale graduale per ridurre il rumore della stima."""
    return cv2.GaussianBlur(img, (0, 0), sigma)


def sample_preview(img: np.ndarray, w: int, h: int) -> np.ndarray:
    """Prepara un'immagine ridotta per diagnostica, senza modificare i crop nativi."""
    if img.dtype == np.uint16:
        # Solo per la preview. I crop nativi mantengono il bit depth.
        img = (img >> 8).astype(np.uint8)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def find_center(score: np.ndarray, allowed: np.ndarray, selected: list[tuple[int, int]],
                sep: int, fallback: tuple[int, int]) -> tuple[int, int]:
    """Sceglie una zona candidata dal punteggio, evitando quelle già selezionate."""
    h, w = score.shape
    ranked = np.where(allowed, blur(score.astype(np.float32), 14.0), -1.0)
    for x, y in selected:
        cv2.circle(ranked, (x, y), sep, -1, thickness=-1)
    flat = int(np.argmax(ranked))
    if ranked.flat[flat] <= 0:
        return fallback
    y, x = np.unravel_index(flat, ranked.shape)
    return int(x), int(y)


def crop_origin(center: tuple[int, int], crop: int, width: int, height: int) -> tuple[int, int]:
    """Calcola l'angolo del ritaglio mantenendolo dentro l'immagine."""
    x, y = center
    return max(0, min(width - crop, x - crop // 2)), max(0, min(height - crop, y - crop // 2))


def normalized_crop(rgb: np.ndarray, gain_small: np.ndarray, x0: int, y0: int,
                    crop: int, native_w: int, native_h: int) -> np.ndarray:
    """Applica soltanto al ritaglio il guadagno lento stimato dal Test 02."""
    small_h, small_w = gain_small.shape[:2]
    xx = (np.arange(x0, x0 + crop, dtype=np.float32) + 0.5) * small_w / native_w - 0.5
    yy = (np.arange(y0, y0 + crop, dtype=np.float32) + 0.5) * small_h / native_h - 0.5
    mx, my = np.meshgrid(xx, yy)
    gain = cv2.remap(gain_small, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    info = np.iinfo(rgb.dtype)
    scale = float(info.max) / 255.0
    patch = rgb[y0:y0 + crop, x0:x0 + crop].astype(np.float32) / scale
    return np.rint(np.clip(patch * gain, 0, 255) * scale).astype(rgb.dtype)


def to8(rgb: np.ndarray) -> np.ndarray:
    """Converte una copia di lavoro a 8 bit per le sole anteprime."""
    return rgb if rgb.dtype == np.uint8 else (rgb >> 8).astype(np.uint8)


def tile(rgb: np.ndarray, label: str) -> np.ndarray:
    """Inserisce il ritaglio in un pannello con l'etichetta della sorgente."""
    rgb8 = to8(rgb)
    height, width = rgb8.shape[:2]
    canvas = np.full((height + 30, width, 3), (27, 27, 27), np.uint8)
    canvas[30:] = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    cv2.putText(canvas, label, (7, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.49,
                (245, 245, 245), 1, cv2.LINE_AA)
    return canvas


def run(root: Path, out: Path, crop: int):
    """Confronta Base, donatori e Test 02 su zone candidate, senza correggere i TIFF."""
    step2 = load_step2(root)
    base_path, donor_paths, mask_paths = step2.percorsi(root)
    corrected_path = root / 'output' / '02_analisi_riflessi' / 'test_02' / '01_correzione_globale.tif'
    required = [base_path, *donor_paths, *mask_paths, corrected_path]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError('Mancano file delle fasi 1/2:\n' + '\n'.join(map(str, missing)))
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Output gia presente: {out}. Scegli --out per un nuovo test.')
    if out == root or out == root / 'images' or root / 'images' in out.parents:
        raise ValueError('La destinazione non puo essere images/ o la radice del progetto.')

    print('Lettura Base, quattro donatori e risultato del Test 02...')
    base = step2.apri_rgb(base_path)
    donors = [step2.apri_rgb(p) for p in donor_paths]
    corrected = step2.apri_rgb(corrected_path)
    if base.ndim != 3 or base.shape[2] != 3 or base.dtype not in (np.uint8, np.uint16):
        raise ValueError('Sono richiesti TIFF RGB uint8 o uint16.')
    h, w, _ = base.shape
    if any(im.shape != base.shape or im.dtype != base.dtype for im in [*donors, corrected]):
        raise ValueError('Base, donatori e Test 02 devono avere risoluzione e dtype identici.')
    if crop > min(w, h):
        raise ValueError(f'--crop={crop} supera il lato minore ({min(w, h)} px).')
    masks = []
    for path in mask_paths:
        mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != (h, w):
            raise ValueError(f'Maschera di registrazione assente o di dimensioni errate: {path}')
        masks.append(mask)

    pw, ph = max(1, round(w / SCALE)), max(1, round(h / SCALE))
    base_p = sample_preview(base, pw, ph)
    corrected_p = sample_preview(corrected, pw, ph)
    donor_p = [sample_preview(im, pw, ph) for im in donors]
    mask_p = [cv2.resize(m, (pw, ph), interpolation=cv2.INTER_NEAREST) for m in masks]

    print('Ricostruzione dei criteri del Test 02 alla sola scala diagnostica...')
    alpha, weights, gains, outline = step2.calcola_mappe(base_p, donor_p, mask_p)
    wood = outline > 0.65
    y_base, y_after = gray(base_p), gray(corrected_p)
    improvement = np.maximum(y_base - y_after, 0)
    # Proxy estetico: differenza di luminosita' rispetto al vicinato e perdita
    # di saturazione. NON implica che la zona sia sicuramente speculare.
    sat = cv2.cvtColor(base_p, cv2.COLOR_RGB2HSV)[:, :, 1].astype(np.float32)
    low_sat = np.clip((blur(sat, 26) - sat + 7.0) / 48.0, 0, 1)
    local_bright = np.clip((y_base - blur(y_base, 28) + 5.0) / 36.0, 0, 1)
    suspect = low_sat * local_bright * (y_base > 55) * wood
    remaining = suspect * (1 - np.clip(improvement / 20.0, 0, 1))
    shape = (outline > 0.15).astype(np.uint8)
    edge = cv2.morphologyEx(shape, cv2.MORPH_GRADIENT,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))) > 0
    border_score = (local_bright * 0.65 + low_sat * 0.35) * edge
    safe = cv2.erode(wood.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0

    margin = max(1, int(np.ceil(crop / (2 * SCALE))))
    allowed = np.zeros((ph, pw), bool)
    allowed[margin:max(margin, ph - margin), margin:max(margin, pw - margin)] = True
    mid = (pw // 2, ph // 2)
    chosen = []
    sep = max(20, crop // SCALE)
    areas = [
        ('01_zona_migliorata', improvement, safe),
        ('02_riflesso_residuo', remaining, safe),
        ('03_bordo', border_score, edge),
        ('04_legno_controllo', blur(sat, 8) / 255.0, safe & (improvement < 1.0)),
    ]
    centers = []
    for name, score, eligible in areas:
        center = find_center(score, eligible & allowed, chosen, sep, mid)
        chosen.append(center)
        centers.append((name, center))

    out.mkdir(parents=True)
    # Immagine di orientamento; rettangoli nativi proiettati sulla preview.
    annotated = cv2.cvtColor(base_p.copy(), cv2.COLOR_RGB2BGR)
    colors = [(0, 210, 70), (40, 175, 245), (220, 160, 25), (215, 120, 220)]
    report = ['# Fase 2 / Test 03 — Verifica delle aree da migliorare', '',
              f'- Sorgenti: {w} × {h} px, {base.dtype}.',
              '- Nessuna correzione applicata: Test 02 e TIFF originali invariati.',
              '- Le aree sono proposte automaticamente con criteri euristici, non sono riflessi certificati.',
              '', '| Area | Centro nativo (x, y) | Delta luminosita medio Base−Test02 |',
              '| --- | --- | ---: |']
    for i, (name, (sx, sy)) in enumerate(centers):
        nx = min(w - 1, round((sx + 0.5) * w / pw))
        ny = min(h - 1, round((sy + 0.5) * h / ph))
        x0, y0 = crop_origin((nx, ny), crop, w, h)
        rect = (round(x0 * pw / w), round(y0 * ph / h),
                round((x0 + crop) * pw / w), round((y0 + crop) * ph / h))
        cv2.rectangle(annotated, rect[:2], rect[2:], colors[i], 2)
        cv2.putText(annotated, str(i + 1), (rect[0] + 3, max(15, rect[1] + 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, colors[i], 2, cv2.LINE_AA)
        before = base[y0:y0 + crop, x0:x0 + crop]
        after = corrected[y0:y0 + crop, x0:x0 + crop]
        raws = [d[y0:y0 + crop, x0:x0 + crop] for d in donors]
        matches = [normalized_crop(d, g, x0, y0, crop, w, h)
                   for d, g in zip(donors, gains)]
        labels = ['BASE', 'TEST 02', 'R1 originale', 'R2 originale', 'R3 originale', 'R4 originale']
        top = cv2.hconcat([tile(img, label) for img, label in zip([before, after, *raws], labels)])
        labels2 = ['BASE (ripetuta)', 'TEST 02 (ripetuto)', 'R1 normalizzato',
                   'R2 normalizzato', 'R3 normalizzato', 'R4 normalizzato']
        bottom = cv2.hconcat([tile(img, label) for img, label in zip([before, after, *matches], labels2)])
        cv2.imwrite(str(out / f'{name}.png'), cv2.vconcat([top, bottom]))
        delta = float(np.mean(gray(to8(before)) - gray(to8(after))))
        report.append(f'| {name} | ({nx}, {ny}) | {delta:+.2f}/255 |')
        print(f'  {name}: centro ({nx}, {ny}) / ritaglio {crop} px')

    cv2.imwrite(str(out / '00_zone_su_base.png'), annotated)
    report.extend(['', '## Lettura dei confronti',
                   '- Riga 1: immagini non normalizzate, pixel nativi (nessun resize dei ritagli).',
                   '- Riga 2: donatori con **solo il guadagno fotografico lento** gia usato nel Test 02; non recupera dettaglio mancante.',
                   '- Controllare se le venature sono realmente piu leggibili in qualche donatore, senza aloni o colori falsi.',
                   '- Se nessun donatore offre un miglioramento reale, non aumentare automaticamente la fusione.',
                   '', '## Decisione',
                   'Da completare dopo ispezione visiva a zoom 100%.'])
    (out / 'osservazioni.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print('Output:', out)
    print('Inviare 00_zone_su_base.png e le quattro immagini di confronto per la valutazione.')


def main():
    """Legge root, output e dimensione del crop e avvia la diagnostica."""
    parser = argparse.ArgumentParser(description='Fase 2 Test 03 — verifica della fusione esistente')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2],
                        help='Radice del progetto locale')
    parser.add_argument('--out', type=Path, default=None,
                        help='Cartella di output nuova/vuota')
    parser.add_argument('--crop', type=int, default=512, help='Lato dei crop in pixel nativi')
    args = parser.parse_args()
    if args.crop < 96 or args.crop > 1200:
        parser.error('--crop deve essere tra 96 e 1200 pixel')
    root = args.root.resolve()
    out = (args.out or root / 'output' / '02_analisi_riflessi' / 'test_03').resolve()
    run(root, out, args.crop)


if __name__ == '__main__':
    main()