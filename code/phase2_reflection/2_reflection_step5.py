"""FASE 2 / TEST 05 — Relazione tra Base e quattro illuminazioni singole.

Obiettivo:
    Verificare se le zone candidate a riflesso in Base coincidono con quelle
    osservate nelle fotografie acquisite con le singole luci; stimare inoltre
    quanto Base somigli a una somma dei quattro scatti.

Input:
    images/Base.tif
    output/01_registrazione/test_01/risultato/registered/Riflesso_N_registered.tif
    output/01_registrazione/test_01/diagnostica/masks/Riflesso_N_valid.png

Output (nuovo): output/02_analisi_riflessi/test_05/
    01_mappe_candidati.png       — Base e quattro scatti; arancione = candidato
    02_corrispondenza_base.png  — corrispondenza tra candidati
    03_somma_approssimata.png   — confronto luminosita' Base / somma adattata
    osservazioni.md            — misure, impostazioni, limiti

Fasi:
    1. Riduzione a scala 1:8 SOLO per diagnosi.
    2. Ricerca di eccessi di luminosita' rispetto al contesto locale.
    3. Confronto spaziale delle mappe candidate, senza usare il colore del legno.
    4. Verifica esplorativa di Base ~= a * somma(singoli) + b.

Risultato atteso:
    Capire se l'acquisizione multi-luce offre un indizio utilizzabile per
    individuare i riflessi. Non corregge immagini, non sovrascrive i precedenti.

ATTENZIONE: eccesso locale di luminanza != riflesso certo; bordi, metallo e
texture possono produrre falsi positivi. I TIFF RGB potrebbero non essere
lineari, avere esposizione/WB diversi o clipping. La somma e' soltanto un
modello approssimativo; per una verifica fisica servono RAW linearizzati con
acquisizioni ed esposizioni coerenti.

Esecuzione dalla radice del progetto:
    python code/phase2_reflection/2_reflection_step5.py

Dipendenze: numpy, opencv-python, tifffile (imagecodecs per TIFF compressi).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile


SCALA = 8
SIGMA = 24.0          # scala della variazione luminosa (pixel sull'anteprima)
SOGLIA = 0.11         # contrasto locale relativo minimo
LUMA_MIN = 0.08       # protezione dai falsi segnali nel fondo molto scuro
TOLLERANZA = 5        # pixel di tolleranza per il confronto fra zone


def percorsi(root: Path):
    """Identifica Base, i quattro scatti della Fase 1 e le loro maschere."""
    fase1 = root / 'output' / '01_registrazione' / 'test_01'
    base = root / 'images' / 'Base.tif'
    singoli = [fase1 / 'risultato' / 'registered' /
               f'Riflesso_{i}_registered.tif' for i in range(1, 5)]
    validi = [fase1 / 'diagnostica' / 'masks' /
              f'Riflesso_{i}_valid.png' for i in range(1, 5)]
    return [base, *singoli], validi


def leggi_rgb(path: Path) -> np.ndarray:
    """Apre il TIFF RGB, preferendo accesso a memoria mappata se possibile."""
    try:
        return tifffile.memmap(path)
    except (ValueError, OSError, TypeError):
        try:
            return tifffile.imread(path)
        except (ValueError, OSError, ImportError):
            bgr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if bgr is None or bgr.ndim != 3 or bgr.shape[2] != 3:
                raise ValueError(f'Impossibile leggere TIFF RGB: {path}')
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def anteprima(rgb: np.ndarray, w: int, h: int) -> np.ndarray:
    """Riduce soltanto per la diagnosi; non crea un nuovo TIFF."""
    if rgb.dtype == np.uint16:
        rgb = (rgb >> 8).astype(np.uint8)
    return cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)


def area_soggetto(base8: np.ndarray) -> tuple[np.ndarray, bool]:
    """Stima la regione principale diversa dal fondo, senza soglie di Hue.

    E' solo un supporto diagnostico, non una segmentazione generale: su
    sfondi complessi o simili all'oggetto occorre ispezionarla o usare --roi.
    """
    lum = cv2.cvtColor(base8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    h, w = lum.shape
    band = max(3, min(h, w) // 24)
    border = np.concatenate((lum[:band, :].ravel(), lum[-band:, :].ravel(),
                             lum[:, :band].ravel(), lum[:, -band:].ravel()))
    bg = float(np.median(border))
    amplitude = max(0.0, float(np.percentile(lum, 95) - bg))
    difference = np.abs(lum - bg)
    foreground = (difference > max(0.09, 0.20 * amplitude)).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)
    n, ids, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    if n < 2:
        return np.ones((h, w), bool), False
    best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    component = (ids == best).astype(np.uint8)
    contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    support = np.zeros_like(component)
    cv2.drawContours(support, contours, -1, 1, cv2.FILLED)
    fraction = float(np.mean(support))
    if not 0.04 <= fraction <= 0.85:
        return np.ones((h, w), bool), False
    return support.astype(bool), True


def candidati(rgb8: np.ndarray, valido: np.ndarray, support: np.ndarray,
              sigma: float, soglia: float, luma_min: float) -> tuple[np.ndarray, np.ndarray]:
    """Individua picchi luminosi locali, senza soglie su tonalita' del soggetto.

    Il punteggio e' un contrasto positivo relativo al contesto GaussianBlur.
    La diminuzione di saturazione aggiunge solo un piccolo contributo: non
    viene usata come requisito, per non escludere oggetti grigi o metallici.
    """
    lum = cv2.cvtColor(rgb8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    sat = cv2.cvtColor(rgb8, cv2.COLOR_RGB2HSV)[:, :, 1].astype(np.float32) / 255.0
    # Normalizzazione del contesto solo dentro il supporto: il salto netto
    # tra soggetto e sfondo non deve apparire come un riflesso esteso.
    weight = support.astype(np.float32)
    den = cv2.GaussianBlur(weight, (0, 0), sigma)
    fondo = cv2.GaussianBlur(lum * weight, (0, 0), sigma) / np.maximum(den, 1e-4)
    sat_fondo = cv2.GaussianBlur(sat * weight, (0, 0), sigma) / np.maximum(den, 1e-4)
    contrasto = np.maximum(0.0, lum - fondo) / (fondo + 0.08)
    desaturazione = np.clip((sat_fondo - sat) / 0.35, 0.0, 1.0)
    score = np.clip(contrasto * (0.85 + 0.15 * desaturazione), 0.0, 1.0)
    mask = (score >= soglia) & (lum >= luma_min) & valido & support
    # Un'apertura minima elimina i pixel isolati prodotti dal rumore.
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN,
                            np.ones((3, 3), dtype=np.uint8)).astype(bool)
    return score, mask


def sRGB_lineare(rgb8: np.ndarray) -> np.ndarray:
    """Approssima la luminanza lineare assumendo RGB con curva sRGB standard.

    Non costituisce una calibrazione della risposta della fotocamera.
    """
    x = rgb8.astype(np.float32) / 255.0
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return (0.2126 * lin[:, :, 0] + 0.7152 * lin[:, :, 1] +
            0.0722 * lin[:, :, 2]).astype(np.float32)


def da_lineare_a_grigio(x: np.ndarray) -> np.ndarray:
    """Converte la luminanza lineare in un'anteprima grigia a 8 bit."""
    x = np.clip(x, 0.0, 1.0)
    v = np.where(x <= 0.0031308, 12.92 * x,
                 1.055 * np.power(x, 1.0 / 2.4) - 0.055)
    return np.round(255.0 * v).astype(np.uint8)


def adatta_somma(base_y: np.ndarray, somma_y: np.ndarray,
                 area: np.ndarray) -> tuple[float, float, dict]:
    """Stima Base ~= a * somma + b con una regressione robusta in luminanza.

    Il termine b assorbe una parte delle differenze ambientali e del nero.
    I parametri non vanno interpretati come intensita' fisiche delle luci.
    """
    ys, xs = base_y[area].astype(np.float64), somma_y[area].astype(np.float64)
    if len(xs) < 50:
        raise ValueError('Troppi pochi pixel utilizzabili per il confronto della somma.')
    rng = np.random.default_rng(1505)
    if len(xs) > 70000:
        selected = rng.choice(len(xs), 70000, replace=False)
        xs, ys = xs[selected], ys[selected]
    # Separiamo campioni di stima e controllo per non valutare solo il training.
    shuffled = rng.permutation(len(xs))
    cut = max(30, int(0.8 * len(xs)))
    tr, va = shuffled[:cut], shuffled[cut:]
    x, y = xs[tr], ys[tr]
    a, b = np.linalg.lstsq(np.column_stack((x, np.ones(len(x)))), y, rcond=None)[0]
    a = max(0.0, float(a))
    b = float(np.median(y - a * x))
    for _ in range(6):
        residual = y - (a * x + b)
        mad = 1.4826 * np.median(np.abs(residual - np.median(residual))) + 0.005
        weight = np.minimum(1.0, (1.345 * mad) / np.maximum(np.abs(residual), 1e-6))
        wn = np.sum(weight)
        xm, ym = np.sum(weight * x) / wn, np.sum(weight * y) / wn
        a = max(0.0, float(np.sum(weight * (x - xm) * (y - ym)) /
                           max(1e-9, np.sum(weight * (x - xm) ** 2))))
        b = float(ym - a * xm)
    if len(va) > 0:
        predicted = a * xs[va] + b
        measured = ys[va]
        mae = float(np.mean(np.abs(measured - predicted)))
        r2 = float(1.0 - np.sum((measured - predicted) ** 2) /
                   max(1e-9, np.sum((measured - measured.mean()) ** 2)))
    else:
        mae, r2 = float('nan'), float('nan')
    return a, b, {'n': int(len(xs)), 'mae': mae, 'r2': r2}


def applica_roi(shape: tuple[int, int], scala_shape: tuple[int, int],
                 roi: tuple[int, int, int, int] | None) -> np.ndarray:
    """Ritorna l'area d'analisi; per default tutto il fotogramma."""
    h, w = shape
    sh, sw = scala_shape
    selected = np.ones((sh, sw), dtype=bool)
    if roi is None:
        return selected
    x, y, rw, rh = roi
    if min(x, y) < 0 or min(rw, rh) <= 0 or x + rw > w or y + rh > h:
        raise ValueError(f'ROI non valida per immagine {w}x{h}: {roi}')
    selected[:] = False
    x0, x1 = int(x * sw / w), int(np.ceil((x + rw) * sw / w))
    y0, y1 = int(y * sh / h), int(np.ceil((y + rh) * sh / h))
    selected[y0:y1, x0:x1] = True
    return selected


def aggiungi_titolo(rgb: np.ndarray, testo: str, width: int = 380) -> np.ndarray:
    """Crea un pannello RGB leggibile senza alterare il contenuto sorgente."""
    h, w = rgb.shape[:2]
    hh = int(round(h * width / w))
    tile = cv2.resize(rgb, (width, hh), interpolation=cv2.INTER_AREA)
    panel = np.full((hh + 38, width, 3), 25, dtype=np.uint8)
    panel[38:] = tile
    cv2.putText(panel, testo, (10, 26), cv2.FONT_HERSHEY_SIMPLEX,
                0.57, (245, 245, 245), 1, cv2.LINE_AA)
    return panel


def evidenzia(rgb8: np.ndarray, mask: np.ndarray,
               tint: tuple[int, int, int] = (255, 75, 35)) -> np.ndarray:
    """Sovrappone un colore alle zone candidate; non corregge l'immagine."""
    out = rgb8.copy()
    colore = np.asarray(tint, dtype=np.float32)
    out[mask] = np.rint(out[mask].astype(np.float32) * 0.35 +
                        colore * 0.65).astype(np.uint8)
    return out


def salva_png(path: Path, image_rgb: np.ndarray) -> None:
    """Salva un'anteprima in PNG RGB e segnala errori di scrittura."""
    if not cv2.imwrite(str(path), cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f'Impossibile salvare {path}')


def esegui(root: Path, out: Path, soglia: float, sigma: float,
           luma_min: float, tolleranza: int,
           roi: tuple[int, int, int, int] | None) -> None:
    """Genera mappe, corrispondenze e una verifica esplorativa della somma."""
    root, out = root.resolve(), out.resolve()
    paths, mask_paths = percorsi(root)
    required = [*paths, *mask_paths]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError('File necessari mancanti:\n' + '\n'.join(map(str, missing)))
    if out == root or out == root / 'images' or root / 'images' in out.parents:
        raise ValueError('La destinazione non puo essere la root o images/.')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Output gia presente: {out}. Usa --out con cartella nuova.')

    print('Carico anteprime delle cinque illuminazioni...')
    rgb_files = [leggi_rgb(p) for p in paths]
    h, w, c = rgb_files[0].shape
    dtype = rgb_files[0].dtype
    if c != 3 or dtype not in (np.uint8, np.uint16):
        raise ValueError('Sono previsti TIFF RGB a 8 o 16 bit.')
    if any(im.shape != (h, w, 3) or im.dtype != dtype for im in rgb_files):
        raise ValueError('Le immagini registrate devono avere dimensione e tipo di Base.')
    sw, sh = max(1, round(w / SCALA)), max(1, round(h / SCALA))
    previews = [anteprima(im, sw, sh) for im in rgb_files]
    del rgb_files
    validi = []
    for p in mask_paths:
        mask = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != (h, w):
            raise ValueError(f'Maschera di validita assente o con dimensioni errate: {p}')
        validi.append(cv2.resize(mask, (sw, sh), interpolation=cv2.INTER_NEAREST) > 0)
        del mask
    area = applica_roi((h, w), (sh, sw), roi)
    support, estimated_support = area_soggetto(previews[0])
    area &= support
    allowed_any = np.logical_or.reduce(validi) & area
    allowed_all = np.logical_and.reduce(validi) & area
    scores, flags = [], []
    for i, im in enumerate(previews):
        permitted = area if i == 0 else (area & validi[i - 1])
        score, mask = candidati(im, permitted, support, sigma, soglia, luma_min)
        scores.append(score)
        flags.append(mask)
    base_c = flags[0] & allowed_any
    singles_c = [m & area for m in flags[1:]]
    union = np.logical_or.reduce(singles_c)
    if tolleranza:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                     (2 * tolleranza + 1, 2 * tolleranza + 1))
        union_near = cv2.dilate(union.astype(np.uint8), k).astype(bool)
    else:
        union_near = union
    comune = base_c & union_near
    solo_base = base_c & (~union_near)
    solo_singoli = union & (~base_c)

    print('Verifico una somma approssimata delle luminanze...')
    linear = [sRGB_lineare(im) for im in previews]
    base_linear = linear[0]
    sum_linear = np.sum(linear[1:], axis=0)
    no_clip = np.logical_and.reduce([np.max(im, axis=2) < 248 for im in previews])
    fit_area = allowed_all & no_clip & (base_linear > 0.025) & (sum_linear > 0.025)
    fit_ok = int(np.count_nonzero(fit_area)) >= 50
    if fit_ok:
        a, b, metrics = adatta_somma(base_linear, sum_linear, fit_area)
        predicted = a * sum_linear + b
        residual = base_linear - predicted
    else:
        a, b, metrics = float('nan'), float('nan'), {'n': 0, 'mae': float('nan'), 'r2': float('nan')}
        predicted = np.zeros_like(base_linear)
        residual = np.zeros_like(base_linear)

    out.mkdir(parents=True, exist_ok=True)
    titles = ['Base (4 luci)', 'Luce 1', 'Luce 2', 'Luce 3', 'Luce 4']
    panorama = np.hstack([
        aggiungi_titolo(evidenzia(rgb, mask), title)
        for rgb, mask, title in zip(previews, flags, titles)
    ])
    salva_png(out / '01_mappe_candidati.png', panorama)

    palette = previews[0].copy()
    palette[solo_base] = (238, 64, 176)       # magenta = solo Base
    palette[solo_singoli] = (50, 219, 96)     # verde = solo singoli
    palette[comune] = (255, 211, 52)          # giallo = corrispondenza
    maps = np.hstack([
        aggiungi_titolo(evidenzia(previews[0], base_c), 'Candidati Base'),
        aggiungi_titolo(evidenzia(previews[0], union, (50, 230, 95)), 'Unione 4 luci'),
        aggiungi_titolo(palette, 'Giallo: coincidenza'),
    ])
    salva_png(out / '02_corrispondenza_base.png', maps)

    if fit_ok:
        residual_norm = np.clip(residual / 0.2, -1.0, 1.0)
        # Blu: somma stimata piu' luminosa di Base. Rosso: Base piu' luminosa.
        residuo_rgb = np.stack([
            np.where(residual_norm >= 0, 128 + residual_norm * 127, 128 + residual_norm * 110),
            128 - np.abs(residual_norm) * 80,
            np.where(residual_norm <= 0, 128 - residual_norm * 127, 128 - residual_norm * 110),
        ], axis=2).clip(0, 255).astype(np.uint8)
    else:
        residuo_rgb = np.full((sh, sw, 3), 127, dtype=np.uint8)
    pred8 = da_lineare_a_grigio(predicted)
    somma_plot = np.hstack([
        aggiungi_titolo(previews[0], 'Base originale'),
        aggiungi_titolo(cv2.cvtColor(pred8, cv2.COLOR_GRAY2RGB), 'Somma adattata'),
        aggiungi_titolo(residuo_rgb, 'Residuo: rosso / blu'),
    ])
    salva_png(out / '03_somma_approssimata.png', somma_plot)

    base_count = int(np.count_nonzero(base_c))
    coinc_count = int(np.count_nonzero(comune))
    factor = 100 * coinc_count / base_count if base_count else None
    factor_label = f'{factor:.1f}%' if factor is not None else "non calcolabile (nessun candidato in Base)"
    by_light = [int(np.count_nonzero(base_c & mask)) for mask in singles_c]
    content = (
        '# Fase 2 / Test 05 — Confronto multi-illuminazione\n\n'
        f'- Origine: {w} × {h} px; analisi a {sw} × {sh} px (scala 1:{SCALA}).\n'
        f'- Area considerata: {"intero fotogramma" if roi is None else str(roi)}; supporto stimato={estimated_support}, area finale={100*np.mean(area):.1f}% preview.\n'
        f'- Parametri: sigma={sigma:.1f}, soglia={soglia:.3f}, '
        f'luminosita minima={luma_min:.3f}, tolleranza={tolleranza} px preview.\n'
        f'- Pixel candidati in Base, nell\'area valida: {base_count:,}.\n'
        f'- Pixel candidati di Base vicini ad almeno un candidato singolo: '
        f'{coinc_count:,} ({factor_label} dei candidati di Base).\n'
        f'- Pixel candidati di Base senza supporto singolo vicino: '
        f'{int(np.count_nonzero(solo_base)):,}.\n'
        f'- Coincidenza esatta Base/scatti 1–4 (pixel preview): '
        f'{", ".join(str(v) for v in by_light)}.\n\n'
        '## Somma approssimata\n\n'
        'Assumendo provvisoriamente una curva sRGB standard, si testa '
        'L_Base ≈ a × (L1+L2+L3+L4) + b sui pixel non saturi. '
        'Il fit usa campioni distinti per stima e controllo.\n\n'
        f'- Pixel campionati per fit: {metrics["n"]:,}.\n'
        f'- a = {a:.5f}; b = {b:.5f} (NON sono coefficienti fisici).\n'
        f'- MAE holdout (luminosita lineare 0–1): {metrics["mae"]:.5f}.\n'
        f'- R² holdout: {metrics["r2"]:.4f}.\n\n'
        '## Interpretazione e limiti\n\n'
        '- Rosso/arancio nella prima figura indica un **candidato**, non un riflesso certo.\n'
        '- Nella seconda: **giallo** = candidati Base vicini a una luce singola; '
        '**magenta** = solo Base; **verde** = solo singoli.\n'
        '- Nell’ultima: rosso = Base piu luminosa della somma adattata; '
        'blu = somma stimata piu luminosa di Base.\n'
        '- La stima del soggetto usa differenza di luminanza rispetto ai bordi del frame, non il colore del legno; potrebbe fallire su altri fondali.\n'
        '- Il rilevatore puo confondere contorni, ponticello, texture e parti metalliche '
        'con riflessi. Non assume un colore o una sagoma specifica del violino.\n'
        '- Lo score misura eccessi locali, non picchi piatti molto estesi e saturi.\n'
        '- La tolleranza sulla posizione non certifica che sia lo stesso riflesso.\n'
        '- Somma non direttamente valida per RGB con tono non lineare, clipping, '
        'esposizioni/bilanciamenti diversi o contributo di luce ambientale.\n'
        '- Nessun originale, registrato, Test 02, 03 o 04 e stato modificato.\n\n'
        '## Decisione\n\n'
        'Da compilare dopo ispezione visiva dei tre PNG sul dataset reale: '
        'valutare corrispondenze sulla macchia principale e falsi positivi '
        'prima di modificare la fusione del Test 02.\n'
    )
    (out / 'osservazioni.md').write_text(content, encoding='utf-8')
    for name in ['01_mappe_candidati.png', '02_corrispondenza_base.png',
                 '03_somma_approssimata.png', 'osservazioni.md']:
        print('Creato:', out / name)
    print(f'Corrispondenza candidati Base: {factor_label} (non e un tasso di riflessi rilevati)')


def main() -> None:
    """Legge i parametri senza imporre ROI o soglie dipendenti dal violino."""
    parser = argparse.ArgumentParser(description='Test 05: indizi di riflesso e somma delle 4 illuminazioni')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path, default=None,
                        help='Cartella nuova/vuota; default: output/.../test_05')
    parser.add_argument('--sigma', type=float, default=SIGMA)
    parser.add_argument('--threshold', type=float, default=SOGLIA)
    parser.add_argument('--min-luma', type=float, default=LUMA_MIN)
    parser.add_argument('--tolerance', type=int, default=TOLLERANZA)
    parser.add_argument('--roi', nargs=4, metavar=('X', 'Y', 'W', 'H'), type=int,
                        help='Regione facoltativa in coordinate originali; default: intera immagine')
    args = parser.parse_args()
    if args.sigma < 2 or args.sigma > 100 or not 0 < args.threshold < 1 or not 0 <= args.min_luma < 1:
        parser.error('Controlla sigma (2-100), threshold (0-1) e min-luma (0-1).')
    if not 0 <= args.tolerance <= 50:
        parser.error('--tolerance deve essere tra 0 e 50')
    root = args.root.resolve()
    out = (args.out or root / 'output' / '02_analisi_riflessi' / 'test_05').resolve()
    esegui(root, out, args.threshold, args.sigma, args.min_luma, args.tolerance,
           tuple(args.roi) if args.roi else None)


if __name__ == '__main__':
    main()