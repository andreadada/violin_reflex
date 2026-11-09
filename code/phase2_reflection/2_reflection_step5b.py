"""FASE 2 / TEST 05B — Dove i donatori offrono informazioni più utili?

Obiettivo:
    Individuare zone di Base che sembrano più luminose dei singoli scatti,
    dopo un bilanciamento fotografico prudente, e valutare se un donatore
    conserva un dettaglio locale più leggibile.

Input:
    images/Base.tif
    output/01_registrazione/test_01/risultato/registered/Riflesso_N_registered.tif
    output/01_registrazione/test_01/diagnostica/masks/Riflesso_N_valid.png

Output (nuovo): output/02_analisi_riflessi/test_05b/
    01_evidenza_base.png       — ipotesi di miglioramento sulle aree candidate
    02_scelta_donatori.png     — score, scelta donatore e texture relativa
    03_confronti_nativi.png   — Base/donatore grezzo/normalizzato in tre zone
    osservazioni.md          — misure, limiti e parametri

Fasi:
    1. Semplificare le immagini a scala 1:8, SOLO per l'analisi delle mappe.
    2. Compensare lentamente la diversa esposizione di ciascun donatore,
       senza soglie di tonalità o maschere costruite per il legno arancione.
    3. Stimare per ciascun donatore: eccesso luminoso di Base, dettaglio
       relativo e affidabilità del campione originale.
    4. Verificare tre zone su crop a PIXEL NATIVI; nessuna fusione eseguita.

Risultato atteso:
    Capire se emergono candidati più selettivi del Test 05 e se le zone
    scelte contengono veramente più texture nella foto donatrice.

Limiti:
    Le mappe NON sono riflessi certificati. Le ombre possono produrre
    falsi positivi; gradienti e microcontrasto non sono necessariamente
    texture autentica. La stima dell'oggetto può fallire su sfondi complessi.
    L'analisi 1:8 non misura le venature più sottili: controllare i crop.

Esecuzione dalla radice del progetto:
    python code/phase2_reflection/2_reflection_step5b.py

Richiede 2_reflection_step5.py nella stessa cartella. Non altera i TIFF.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import cv2
import numpy as np


SCALA = 8
SIGMA_GAIN = 32.0     # lentezza del bilanciamento, sulla mappa 1:8
SOGLIA_SCORE = 0.09  # solo diagnostica, NON probabilità
LATO_CROP = 512      # crop 1:1 sull'immagine originale


def importa_test05():
    """Riusa lettura TIFF, supporto neutro e pannelli già verificati nel Test 05."""
    path = Path(__file__).resolve().with_name('2_reflection_step5.py')
    if not path.is_file():
        raise FileNotFoundError(f'Serve lo script Test 05 nella stessa cartella: {path}')
    spec = importlib.util.spec_from_file_location('violin_test05', path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Impossibile importare {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def luminanza(rgb: np.ndarray) -> np.ndarray:
    """Luminosità RGB su scala 0–1; è fotografica, non radiometrica."""
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0


def filtro_gaussiano(image: np.ndarray, sigma: float) -> np.ndarray:
    """Applica una media spaziale graduale, mantenendo la dimensione originale."""
    return cv2.GaussianBlur(image, (0, 0), sigma)


def guadagno_lento(base: np.ndarray, donor: np.ndarray,
                   eligible: np.ndarray, sigma: float) -> tuple[np.ndarray, float]:
    """Bilancia il donatore con rapporti di luminanza robusti e spatialmente lenti.

    Esclude dalle stime neri, pixel quasi saturi e rapporti estremi.
    Il guadagno usa il contesto del soggetto: non corregge pixel per pixel.
    """
    usable = eligible & (base > .10) & (donor > .10) & (base < .88) & (donor < .88)
    if np.count_nonzero(usable) < 80:
        return np.ones_like(base, dtype=np.float32), 0.0
    ratio = np.log((base + .04) / (donor + .04))
    median = float(np.median(ratio[usable]))
    stable = usable & (np.abs(ratio - median) < .60)
    if np.count_nonzero(stable) < 80:
        stable = usable
    weights = stable.astype(np.float32)
    den = filtro_gaussiano(weights, sigma)
    numerator = filtro_gaussiano(np.clip(ratio, -1.0, 1.0) * weights, sigma)
    log_gain = np.where(den > 0.03, numerator / np.maximum(den, 1e-5), median)
    gain = np.exp(np.clip(log_gain, np.log(.55), np.log(2.6))).astype(np.float32)
    return gain, float(np.mean(stable))


def dettaglio_locale(lum: np.ndarray) -> np.ndarray:
    """Energia locale delle variazioni fini, per diagnosi e NON per misurare venature vere."""
    high = lum - filtro_gaussiano(lum, 1.2)
    return np.sqrt(np.maximum(filtro_gaussiano(high * high, 3.0), 0))


def score_donatore(base_y: np.ndarray, donor_y: np.ndarray, gain: np.ndarray,
                   detail_base: np.ndarray, support: np.ndarray,
                   valid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Combina differenza fotometrica, dettaglio e rischio di ombra.

    Un donatore è interessante solo se presenta un eccesso relativo di Base,
    ha un'esposizione originale utilizzabile e conserva un po' più di microcontrasto.
    La qualità del microcontrasto è un indizio, non una misura di verità.
    """
    norm_y = np.clip(donor_y * gain, 0, 1)
    difference = np.clip((base_y - norm_y - .025) / .16, 0, 1)
    detail_donor = dettaglio_locale(norm_y)
    improvement = np.clip((detail_donor - detail_base - .001) / .017, 0, 1)
    # Penalizza scatti sottoesposti, anche se amplificabili artificialmente.
    exposure = np.clip((donor_y - .09) / .23, 0, 1)
    # Non sostituiamo zone dove il donatore normalizzato è molto più scuro:
    # potrebbe essere un'ombra e non un vero recupero di superficie.
    shadow_guard = np.clip((norm_y / np.maximum(base_y, .08) - .38) / .34, 0, 1)
    valid_area = support & valid & (donor_y < .96) & (base_y > .09)
    score = (difference * (.22 + .78 * improvement) * exposure * shadow_guard
             * valid_area.astype(np.float32))
    # Evita granulosità in mappa. Per sicurezza riapplica la validità.
    score = filtro_gaussiano(score, 1.7) * valid_area.astype(np.float32)
    return score, improvement, norm_y


def pseudo_colore(heat: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Visualizza uno score 0..1, nero quando non è valida l'area."""
    im = np.uint8(np.clip(heat, 0, 1) * 255)
    col = cv2.cvtColor(cv2.applyColorMap(im, cv2.COLORMAP_VIRIDIS), cv2.COLOR_BGR2RGB)
    col[~allowed] = (20, 20, 20)
    return col


def overlay(base: np.ndarray, heat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Sovrappone rosso/arancio alle zone con score elevato (solo diagnostica)."""
    rgb = base.copy()
    intensity = np.clip(heat[mask], 0, 1)[:, None]
    tint = np.array([255, 67, 39], dtype=np.float32)
    rgb[mask] = np.uint8(np.rint(rgb[mask] * (1 - .65 * intensity) + tint * (.65 * intensity)))
    return rgb


def scegli_centri(score: np.ndarray, support: np.ndarray,
                   threshold: float, crop: int, scale: int) -> list[tuple[str, int, int]]:
    """Seleziona automaticamente due zone candidate lontane e un controllo sano.

    La selezione è euristica: le tre aree devono essere valutate manualmente.
    Non introduce ROI di un violino specifico nell'algoritmo.
    """
    sh, sw = score.shape
    sep = max(10, int(crop / scale * .95))
    # Evita tagli ai bordi quando possibile.
    safe = cv2.erode(support.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    if not np.any(safe):
        safe = support.copy()
    smooth = filtro_gaussiano(score, 6.0)
    available = safe.copy()
    selected = []
    for name in ('candidato_1', 'candidato_2'):
        candidate = np.where(available & (score >= threshold * .4), smooth, -1)
        idx = int(np.argmax(candidate))
        if candidate.flat[idx] < 0:
            break
        y, x = np.unravel_index(idx, score.shape)
        selected.append((name, int(x), int(y)))
        yy, xx = np.ogrid[:sh, :sw]
        available &= (xx - int(x))**2 + (yy - int(y))**2 > sep**2
    # Il controllo è scelto in una zona lontana dai candidati e non troppo piatta.
    control = available & (score < threshold * .25) & safe
    if np.any(control):
        dist = cv2.distanceTransform((safe & (~(score > threshold))).astype(np.uint8),
                                     cv2.DIST_L2, 3)
        idx = int(np.argmax(np.where(control, dist, -1)))
        y, x = np.unravel_index(idx, score.shape)
        selected.append(('controllo', int(x), int(y)))
    return selected


def ritaglio(array: np.ndarray, x: int, y: int, crop: int) -> np.ndarray:
    """Estrae un crop a pixel nativi centrato nel punto indicato."""
    h, w = array.shape[:2]
    crop = min(crop, h, w)
    x0 = max(0, min(w - crop, x - crop // 2))
    y0 = max(0, min(h - crop, y - crop // 2))
    return array[y0:y0 + crop, x0:x0 + crop]


def misura_dettaglio_native(crop: np.ndarray) -> float:
    """Stima il microcontrasto del ritaglio, non identifica la texture del materiale."""
    lum = luminanza(crop)
    high = lum - filtro_gaussiano(lum, 1.3)
    return float(np.sqrt(np.mean(high * high)))


def crea_confronti(base_native: np.ndarray, donor_native: list[np.ndarray],
                    scores: np.ndarray, gains: list[np.ndarray],
                    best: np.ndarray, centers: list[tuple[str, int, int]],
                    scale: int, crop: int, save_png, out: Path) -> list[dict]:
    """Confronta alle coordinate originali Base, donatore e versione bilanciata."""
    h, w = base_native.shape[:2]
    sh, sw = scores.shape
    panels, rows = [], []
    for name, sx, sy in centers:
        dx = min(w-1, int((sx + .5) * w / sw))
        dy = min(h-1, int((sy + .5) * h / sh))
        idx = int(best[sy, sx])
        if name == 'controllo':
            # Diagnosi dello scatto più leggibile nel controllo senza scegliere
            # in base al tipo di materiale.
            idx = int(best[sy, sx])
        base_crop = ritaglio(base_native, dx, dy, crop)
        donor_crop = ritaglio(donor_native[idx], dx, dy, crop)
        g = float(gains[idx][sy, sx])
        balanced = np.uint8(np.clip(donor_crop.astype(np.float32) * g, 0, 255))
        native_base = misura_dettaglio_native(base_crop)
        native_donor = misura_dettaglio_native(balanced)
        label = f'{name}: ({dx}, {dy}), R{idx + 1}, score={scores[sy,sx]:.3f}'
        # Mostriamo in RGB puro i tre ritagli; il testo è fuori dall'immagine.
        row = np.hstack((base_crop, donor_crop, balanced))
        head = np.full((58, row.shape[1], 3), 25, dtype=np.uint8)
        cv2.putText(head, label, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, .64,
                    (247,247,247), 1, cv2.LINE_AA)
        for j, caption in enumerate(('Base', f'R{idx + 1} originale', f'R{idx + 1} bilanciata (g={g:.2f})')):
            cv2.putText(head, caption, (12 + j * base_crop.shape[1], 48),
                        cv2.FONT_HERSHEY_SIMPLEX, .56, (206,206,206), 1, cv2.LINE_AA)
        panels.append(np.vstack((head, row)))
        rows.append(dict(zona=name, center=(dx,dy),donor=idx+1,score=float(scores[sy,sx]),
                         gain=g,detail_base=native_base,detail_donor=native_donor))
    if panels:
        save_png(out / '03_confronti_nativi.png', np.vstack(panels))
    return rows


def run(root: Path, out: Path, threshold: float, gain_sigma: float, crop: int) -> None:
    """Esegue il Test 05B senza generare una fotografia corretta."""
    root, out = root.resolve(), out.resolve()
    test05 = importa_test05()
    paths, mask_paths = test05.percorsi(root)
    missing = [p for p in [*paths, *mask_paths] if not p.is_file()]
    if missing:
        raise FileNotFoundError('File input mancanti:\n'+'\n'.join(map(str,missing)))
    if out == root or out == root/'images' or root/'images' in out.parents:
        raise ValueError('La destinazione non può essere la root del progetto o images/.')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Cartella output già piena: {out}. Usa --out con una nuova cartella.')

    print('Leggo le cinque fotografie per la diagnostica...')
    raw = [test05.leggi_rgb(p) for p in paths]
    h, w, ch = raw[0].shape
    if ch != 3 or raw[0].dtype != np.uint8:
        raise ValueError('Per questa prova sono richiesti TIFF RGB uint8.')
    if any(im.shape != (h,w,3) or im.dtype != np.uint8 for im in raw):
        raise ValueError('Tutti i TIFF devono essere RGB uint8 e della stessa dimensione.')
    sw, sh = max(1, round(w/SCALA)), max(1, round(h/SCALA))
    previews = [test05.anteprima(im, sw, sh) for im in raw]
    masks = []
    for path in mask_paths:
        mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != (h,w):
            raise ValueError(f'Maschera di validità errata: {path}')
        masks.append(cv2.resize(mask,(sw,sh),interpolation=cv2.INTER_NEAREST)>0)

    support, estimated = test05.area_soggetto(previews[0])
    base_y = luminanza(previews[0])
    detail_base = dettaglio_locale(base_y)
    all_scores, details, gains = [], [], []
    for donor, valid in zip(previews[1:], masks):
        donor_y = luminanza(donor)
        gain, _ = guadagno_lento(base_y, donor_y, support & valid, gain_sigma)
        score, detail, _ = score_donatore(base_y, donor_y, gain, detail_base, support, valid)
        gains.append(gain)
        details.append(detail)
        all_scores.append(score)
    stack = np.stack(all_scores, axis=0)
    best = np.argmax(stack, axis=0)
    score = stack.max(axis=0)
    candidates = (score >= threshold) & support
    # Non calcoliamo una percentuale di veri riflessi: non abbiamo ground truth.
    count = int(np.count_nonzero(candidates))
    distribution = [int(np.count_nonzero(candidates & (best == i))) for i in range(4)]
    out.mkdir(parents=True, exist_ok=True)

    test05.salva_png(out/'01_evidenza_base.png', np.hstack([
        test05.aggiungi_titolo(previews[0], 'Base originale'),
        test05.aggiungi_titolo(overlay(previews[0], score, candidates), 'Candidati Test 05B'),
        test05.aggiungi_titolo(pseudo_colore(score, support), 'Evidenza (non probabilita)')
    ]))
    lut = np.array([[34,123,202],[242,157,63],[51,177,111],[172,102,206]],dtype=np.uint8)
    selected = previews[0].copy()
    selected[candidates] = np.uint8(.25*selected[candidates]+.75*lut[best[candidates]])
    texture_by_best = np.take_along_axis(np.stack(details,axis=0), best[None,...], axis=0)[0]
    test05.salva_png(out/'02_scelta_donatori.png', np.hstack([
        test05.aggiungi_titolo(selected, 'Donatori R1 blu / R2 arancio / R3 verde / R4 viola'),
        test05.aggiungi_titolo(pseudo_colore(texture_by_best, support), 'Vantaggio microcontrasto 1:8'),
        test05.aggiungi_titolo(pseudo_colore(score, support), 'Score composto')
    ]))

    centers = scegli_centri(score, support, threshold, crop, SCALA)
    rows = crea_confronti(raw[0],raw[1:],score,gains,best,centers,SCALA,crop,
                          test05.salva_png,out)
    text = [
        '# Fase 2 / Test 05B — Confronto fotometrico e dettaglio',
        '',
        f'- Originali: {w} × {h} px, RGB uint8; mappe: {sw} × {sh} (scala 1:{SCALA}).',
        f'- Soggetto stimato senza soglie Hue: {estimated}; copertura: {100*np.mean(support):.1f}% della mappa.',
        f'- Soglia diagnostica dello score: {threshold:.3f}; sigma del guadagno: {gain_sigma:.1f} px sulla mappa.',
        f'- Candidati Test 05B: {count:,} pixel della mappa ({100*np.mean(candidates):.2f}% del fotogramma).',
        f'- Donatore suggerito nei candidati (R1–R4): {distribution}.',
        '',
        '## Ritagli a pixel nativi',
        '',
        '| Zona | Centro (x,y) | Donatore | Score mappa | Guadagno | Microcontrasto Base | Microcontrasto bilanciato |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: |'
    ]
    for row in rows:
        text.append(f"| {row['zona']} | {row['center']} | R{row['donor']} | {row['score']:.3f} | {row['gain']:.3f} | {row['detail_base']:.4f} | {row['detail_donor']:.4f} |")
    text.extend([
        '',
        '## Cosa verificare manualmente',
        '',
        '- Le aree evidenziate contengono riflessi reali o semplici differenze di luce?',
        '- Il donatore suggerito mostra più venature/dettagli autentici o solo bordi/rumore?',
        '- Corde, tavola colori, sfondo e zone scure producono falsi positivi?',
        '- La normalizzazione cambia troppo l’aspetto del donatore?',
        '',
        '## Limiti',
        '',
        '- Score euristico e soglie numeriche provvisorie: non sono probabilità e non certificano riflessi.',
        '- Il dettaglio nella mappa 1:8 può dipendere da bordi, corde o rumore, non solo dalle venature.',
        '- Il guadagno locale può interpretare diversamente ombre e riflessi; i TIFF non sono dati RAW radiometrici.',
        '- Il supporto usa il contrasto con lo sfondo: non è una segmentazione universale.',
        '- Ritagli e metriche sono diagnostici; per la fusione bisogna preservare geometria e colore.',
        '',
        '**Nessun TIFF è stato modificato; Test 02 rimane la baseline.**',
        '',
        '## Decisione',
        '',
        'Da prendere dopo aver confrontato mappe e ritagli sul dataset reale.'
    ])
    (out/'osservazioni.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    for filename in ('01_evidenza_base.png','02_scelta_donatori.png','03_confronti_nativi.png','osservazioni.md'):
        print('Creato:',out/filename)
    print('Candidati diagnostici:',count,'— non equivale al numero di riflessi reali.')


def main():
    """Legge parametri configurabili e impedisce risultati sovrascritti."""
    parser=argparse.ArgumentParser(description='Test 05B: evidenza multi-illuminazione e dettaglio dei donatori')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out',type=Path,default=None,help='Nuova cartella, default test_05b')
    parser.add_argument('--threshold',type=float,default=SOGLIA_SCORE)
    parser.add_argument('--gain-sigma',type=float,default=SIGMA_GAIN)
    parser.add_argument('--crop',type=int,default=LATO_CROP)
    args=parser.parse_args()
    if not 0.01<=args.threshold<=1 or not 4<=args.gain_sigma<=120 or not 128<=args.crop<=1024:
        parser.error('Parametri: threshold 0.01..1, gain-sigma 4..120, crop 128..1024')
    root=args.root.resolve()
    out=(args.out or root/'output'/'02_analisi_riflessi'/'test_05b').resolve()
    run(root,out,args.threshold,args.gain_sigma,args.crop)


if __name__=='__main__':
    main()
