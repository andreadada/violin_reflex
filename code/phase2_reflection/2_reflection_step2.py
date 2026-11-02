"""FASE 2 / STEP 2 — Prima correzione fotografica selettiva del violino.

Esegui dalla radice di ViolinReflectionRemoval:
    python code/phase2_reflection/2_reflection_step2.py

Input: images/Base.tif, 4 TIFF registrati, 4 maschere di validita' dalla Fase 1.
Output: output/02_analisi_riflessi/test_02/ (TIFF, confronto e mappa).

Criterio: Base resta il riferimento. Un'altra illuminazione contribuisce soltanto
se e' ben esposta, mostra cromaticita' migliore ed e' plausibilmente meno velata
nella zona. La differenza di illuminazione NON prova la presenza di un riflesso.
Non usa le ROI degli esperimenti precedenti e non altera i TIFF sorgente.

Dipendenze: numpy, opencv-python, tifffile; imagecodecs se i TIFF LZW
sono letti con tifffile (altrimenti e' disponibile il fallback OpenCV).


SCHEDA DEL FILE (riferita al progetto locale)
Obiettivo: Provare una prima fusione fotografica automatica per attenuare i riflessi.
Input: Base, quattro TIFF registrati e quattro maschere di validità.
Output: TIFF full-res, mappa e confronto in output/02_analisi_riflessi/test_02/.
Fasi: Maschera cromatica; bilanciamento lento dei donatori; punteggio; fusione a strisce native.
Risultato atteso: Attenuazione parziale dei riflessi mantenendo un aspetto naturale.
Nota: Migliore risultato osservato nel dataset corrente, NON ancora algoritmo generale: la maschera è legata al colore del legno.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile


SCALA_MAPPE = 8                 # solo analisi/anteprima; output TIFF a pixel nativi
STRISCIA = 320                 # righe elaborate insieme per limitare la memoria
ALFA_MAX = 0.85               # forza massima, mai sostituzione integrale di Base
MAX_DELTA_SCURO = 65.0        # protezione dai forti cambi di illuminazione (scala 8 bit)
MAX_DELTA_CHIARO = 22.0


def percorsi(root: Path):
    """Restituisce i percorsi dei cinque TIFF e delle quattro maschere di validità."""
    fase1 = root / 'output' / '01_registrazione' / 'test_01'
    base = root / 'images' / 'Base.tif'
    scatti = [fase1 / 'risultato' / 'registered' / f'Riflesso_{i}_registered.tif'
              for i in range(1, 5)]
    maschere = [fase1 / 'diagnostica' / 'masks' / f'Riflesso_{i}_valid.png'
               for i in range(1, 5)]
    return base, scatti, maschere


def apri_rgb(path: Path) -> np.ndarray:
    """Conserva i valori RGB; usa OpenCV solo come fallback per TIFF compressi."""
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


def anteprima(rgb: np.ndarray, larghezza: int, altezza: int) -> np.ndarray:
    """Ridimensiona un'immagine soltanto per analisi e visualizzazione."""
    if rgb.dtype == np.uint16:
        rgb = (rgb >> 8).astype(np.uint8)
    return cv2.resize(rgb, (larghezza, altezza), interpolation=cv2.INTER_AREA)


def luce(rgb8: np.ndarray) -> np.ndarray:
    """Calcola un indicatore di luminosità RGB, non una misura radiometrica."""
    return cv2.cvtColor(rgb8, cv2.COLOR_RGB2GRAY).astype(np.float32)


def maschera_violino(base8: np.ndarray) -> np.ndarray:
    """Sagoma ricavata dal legno arancio, con interno e bordo inclusi."""
    hsv = cv2.cvtColor(base8, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)
    r, g, b = (base8[:, :, c].astype(np.float32) for c in range(3))
    legno = ((h >= 3) & (h <= 27) & (s > 85) & (v > 45) &
             (r > g * 1.18) & (g > b * 1.04)).astype(np.uint8)
    # La tavola colori e' sotto lo strumento; non deve entrare nella sagoma.
    legno[int(base8.shape[0] * 0.83):] = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    legno = cv2.morphologyEx(legno, cv2.MORPH_CLOSE, kernel)
    n, etichette, stats, _ = cv2.connectedComponentsWithStats(legno, 8)
    if n < 2:
        raise RuntimeError('Impossibile identificare la sagoma del violino.')
    label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest = (etichette == label).astype(np.uint8)
    contours, _ = cv2.findContours(largest, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sagoma = np.zeros_like(largest)
    cv2.drawContours(sagoma, contours, -1, 255, thickness=cv2.FILLED)
    # Sfumatura solo all'interno, per proteggere lo sfondo vicino ai bordi.
    soft = cv2.GaussianBlur(sagoma.astype(np.float32) / 255.0, (0, 0), 1.4)
    return soft * (sagoma.astype(np.float32) / 255.0)


def guadagno_fotografico(base8: np.ndarray, donor8: np.ndarray,
                          sagoma: np.ndarray) -> np.ndarray:
    """Bilancia l'illuminazione usando il legno non abbagliato come riferimento.

    La stima e' locale e lenta; le zone poco sature di Base non contribuiscono
    al calcolo del guadagno, per non ricopiare il riflesso nel donatore.
    """
    sb = cv2.cvtColor(base8, cv2.COLOR_RGB2HSV)[:, :, 1]
    sd = cv2.cvtColor(donor8, cv2.COLOR_RGB2HSV)[:, :, 1]
    yb, yd = luce(base8), luce(donor8)
    affidabili = ((sagoma > 0.9) & (sb > 175) & (sd > 145) &
                  (yb > 48) & (yb < 215) & (yd > 32) & (yd < 215))
    if np.count_nonzero(affidabili) < 80:
        return np.ones((*sb.shape, 3), dtype=np.float32)
    peso = affidabili.astype(np.float32)
    sigma = 24.0  # 192 px circa, al formato nativo
    den = cv2.GaussianBlur(peso, (0, 0), sigma)
    # Prima il guadagno di luminanza; poi una correzione cromatica prudente.
    # Evita che un canale debole (tipicamente il blu del legno arancio)
    # venga amplificato troppo e produca chiazze viola/ciano.
    log_luma = np.log((yb + 8.0) / (yd + 8.0))
    log_luma = np.clip(log_luma, np.log(0.6), np.log(2.7))
    media_luma = float(np.median(log_luma[affidabili]))
    local_luma = np.where(
        den > 0.015,
        cv2.GaussianBlur(log_luma * peso, (0, 0), sigma) / np.maximum(den, 1e-4),
        media_luma,
    )
    gain_luma = np.exp(local_luma).clip(0.6, 2.7)
    gain = np.empty((*sb.shape, 3), dtype=np.float32)
    for c in range(3):
        b = base8[:, :, c].astype(np.float32)
        d = donor8[:, :, c].astype(np.float32)
        log_ratio = np.log((b + 8.0) / (d + 8.0))
        log_ratio = np.clip(log_ratio, np.log(0.6), np.log(2.7))
        media = float(np.median(log_ratio[affidabili]))
        num = cv2.GaussianBlur(log_ratio * peso, (0, 0), sigma)
        local = np.where(den > 0.015, num / np.maximum(den, 1e-4), media)
        gain[:, :, c] = gain_luma * np.exp(
            np.clip(local - local_luma, np.log(0.88), np.log(1.12))
        )
    return gain


def calcola_mappe(base8: np.ndarray, donatori8: list[np.ndarray],
                   validi8: list[np.ndarray]):
    """Mappe leggere: scelta del donatore e intervento automatico globale."""
    sagoma = maschera_violino(base8)
    sat_b = cv2.cvtColor(base8, cv2.COLOR_RGB2HSV)[:, :, 1].astype(np.float32)
    hue_b = cv2.cvtColor(base8, cv2.COLOR_RGB2HSV)[:, :, 0].astype(np.float32)
    lum_b = luce(base8)
    guadagni, punteggi = [], []
    for donor8, valido in zip(donatori8, validi8):
        gain = guadagno_fotografico(base8, donor8, sagoma)
        donor_corr = np.clip(donor8.astype(np.float32) * gain, 0, 255).astype(np.uint8)
        hsv_d = cv2.cvtColor(donor8, cv2.COLOR_RGB2HSV)
        sat_d = hsv_d[:, :, 1].astype(np.float32)
        hue_d = hsv_d[:, :, 0].astype(np.float32)
        lum_d = luce(donor8)
        lum_corr = luce(donor_corr)

        # Indizi combinati: colore meno sbiancato + zona ben esposta +
        # diminuzione plausibile del velo luminoso rispetto a Base.
        colore = np.clip((sat_d - sat_b - 12.0) / 75.0, 0, 1)
        # Una migliore cromaticita' puo' essere utile anche se la luminosita'
        # normalizzata resta quasi uguale a Base.
        velo = np.clip((lum_b - lum_corr + 7.0) / 30.0, 0, 1)
        esposizione = np.clip((lum_d - 30.0) / 45.0, 0, 1)
        hue_delta = np.abs(hue_b - hue_d)
        colore_coerente = (np.minimum(hue_delta, 180 - hue_delta) < 12) | (sat_b < 75)
        affidabilita = (colore_coerente & (valido > 0) & (lum_d < 232)).astype(np.float32)
        score = colore * velo * esposizione * affidabilita * sagoma
        # Zone continue, non una scelta pixel per pixel che crea rumore.
        score = cv2.GaussianBlur(score, (0, 0), 2.4)
        guadagni.append(gain)
        punteggi.append(score)

    stack = np.stack(punteggi, axis=0)
    migliori = np.argmax(stack, axis=0)
    forza = np.clip(stack.max(axis=0) * ALFA_MAX, 0, ALFA_MAX)
    forza[forza < 0.03] = 0.0
    # Confini morbidi fra donatori; forza nulla significa Base immutata.
    selezioni = [cv2.GaussianBlur((migliori == i).astype(np.float32),
                                  (0, 0), 3.0) for i in range(4)]
    normalizzatore = np.maximum(np.sum(selezioni, axis=0), 1e-6)
    pesi = [s / normalizzatore for s in selezioni]
    return forza, pesi, guadagni, sagoma


def scala_striscia(mappa: np.ndarray, y0: int, y1: int, h: int, w: int) -> np.ndarray:
    """Interpola una mappa piccola su righe originali, senza cuciture tra strisce."""
    mh, mw = mappa.shape[:2]
    xs = ((np.arange(w, dtype=np.float32) + 0.5) * mw / w - 0.5)
    ys = ((np.arange(y0, y1, dtype=np.float32) + 0.5) * mh / h - 0.5)
    mx, my = np.meshgrid(xs, ys)
    return cv2.remap(mappa, mx, my, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def icc_originale(path: Path) -> bytes | None:
    """Legge l'eventuale profilo ICC per conservarlo nell'output fotografico."""
    with tifffile.TiffFile(path) as tf:
        tag = tf.pages[0].tags.get(34675)
        return bytes(tag.value) if tag is not None else None


def esegui(root: Path, out: Path, preview_width: int = 760) -> None:
    """Esegue la fusione a risoluzione nativa a strisce e salva TIFF e diagnostiche."""
    base_path, paths, path_valid = percorsi(root)
    mancanti = [p for p in [base_path, *paths, *path_valid] if not p.is_file()]
    if mancanti:
        raise FileNotFoundError('File della Fase 1 mancanti:\n' + '\n'.join(map(str, mancanti)))
    if out == root or out == root / 'images' or root / 'images' in out.parents:
        raise ValueError('La destinazione non puo essere la radice o images/.')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Cartella output non vuota: {out}. Usa --out per un nuovo test.')

    print('Caricamento TIFF originali e registrati...')
    base = apri_rgb(base_path)
    donors = [apri_rgb(p) for p in paths]
    h, w, c = base.shape
    if c != 3 or base.dtype not in (np.uint8, np.uint16):
        raise ValueError('Base deve essere TIFF RGB uint8 o uint16.')
    if any(d.shape != base.shape or d.dtype != base.dtype for d in donors):
        raise ValueError('I TIFF registrati devono avere dimensioni e tipo identici a Base.')
    validi = []
    for p in path_valid:
        m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if m is None or m.shape != (h, w):
            raise ValueError(f'Maschera geometrica assente o errata: {p}')
        validi.append(m)

    # Riduzione utilizzata SOLO per scegliere dove intervenire, non per elaborare
    # o salvare la fotografia finale.
    lw, lh = max(1, round(w / SCALA_MAPPE)), max(1, round(h / SCALA_MAPPE))
    base8 = anteprima(base, lw, lh)
    donor8 = [anteprima(d, lw, lh) for d in donors]
    validi8 = [cv2.resize(m, (lw, lh), interpolation=cv2.INTER_NEAREST) for m in validi]
    print('Analisi globale e scelta delle aree candidate...')
    forza, pesi, guadagni, sagoma = calcola_mappe(base8, donor8, validi8)

    out.mkdir(parents=True, exist_ok=True)
    destinazione = out / '01_correzione_globale.tif'
    icc = icc_originale(base_path)
    extra = [(34675, 'B', len(icc), icc, False)] if icc else None
    output = tifffile.memmap(destinazione, shape=base.shape, dtype=base.dtype,
                             photometric='rgb', metadata=None, extratags=extra)
    valore_max = float(np.iinfo(base.dtype).max)
    fattore = valore_max / 255.0
    modificati = 0
    print('Creazione TIFF a risoluzione originale...')
    for y0 in range(0, h, STRISCIA):
        y1 = min(y0 + STRISCIA, h)
        originale = base[y0:y1].astype(np.float32) / fattore
        corretto = originale.copy()
        alpha = scala_striscia(forza, y0, y1, h, w)
        for i, d in enumerate(donors):
            quota = alpha * scala_striscia(pesi[i], y0, y1, h, w)
            quota *= (validi[i][y0:y1] > 0)
            if float(quota.max()) < 0.002:
                continue
            gain = scala_striscia(guadagni[i], y0, y1, h, w)
            donor_corr = d[y0:y1].astype(np.float32) / fattore * gain
            delta = np.clip(donor_corr - originale,
                            -MAX_DELTA_SCURO, MAX_DELTA_CHIARO)
            corretto += quota[:, :, None] * delta
        modificati += int(np.count_nonzero(np.max(np.abs(corretto - originale), axis=2) >= 1.0))
        output[y0:y1] = np.rint(np.clip(corretto * fattore, 0, valore_max)).astype(base.dtype)
        if y0 == 0 or y1 == h or (y0 // STRISCIA) % 8 == 0:
            print(f'  {y1}/{h} righe')
    output.flush()
    del output

    pw = min(preview_width, w)
    ph = max(1, round(h * pw / w))
    risultato = apri_rgb(destinazione)
    prima = anteprima(base, pw, ph)
    dopo = anteprima(risultato, pw, ph)
    confronto = cv2.hconcat([prima, dopo])
    cv2.imwrite(str(out / '02_prima_dopo.png'), cv2.cvtColor(confronto, cv2.COLOR_RGB2BGR))
    del risultato
    m = cv2.resize(forza, (pw, ph), interpolation=cv2.INTER_LINEAR)
    mappa = cv2.applyColorMap((m * 255 / ALFA_MAX).clip(0, 255).astype(np.uint8),
                             cv2.COLORMAP_VIRIDIS)
    cv2.imwrite(str(out / '03_mappa_intervento.png'), mappa)
    testo = (f'# Fase 2 / Test 02 — Fusione selettiva\n\n'
             f'- Dimensioni: {w} × {h}, {base.dtype}.\n'
             f'- Pixel modificati di almeno 1 livello su scala 8 bit: {modificati:,} '
             f'({100 * modificati / (h*w):.2f}% del fotogramma).\n'
             f'- Area eleggibile (sagoma): {100 * np.mean(sagoma > 0.1):.2f}% della preview.\n'
             f'- Alpha medio sulle aree candidate: '
             f'{float(forza[forza > 0].mean() if np.any(forza > 0) else 0):.3f}.\n\n'
             'Risultato sperimentale: controllare bordi, effe, venature e colore '
             'a zoom 100%. La differenza fra illuminazioni non prova la rimozione '
             'fisica dei riflessi.\n')
    (out / 'osservazioni.md').write_text(testo, encoding='utf-8')
    print('Salvato:', destinazione)
    print('Anteprima:', out / '02_prima_dopo.png')
    print('Nessun TIFF sorgente e stato modificato.')


def main() -> None:
    """Legge le opzioni CLI e avvia il Test 02 senza sovrascrivere risultati precedenti."""
    parser = argparse.ArgumentParser(description='Fase 2, primo test globale di riduzione dei riflessi')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2],
                        help='Cartella ViolinReflectionRemoval')
    parser.add_argument('--out', type=Path, default=None,
                        help='Directory vuota di destinazione (default: test_02)')
    parser.add_argument('--preview-width', type=int, default=760)
    args = parser.parse_args()
    if not (200 <= args.preview_width <= 1600):
        parser.error('--preview-width deve essere fra 200 e 1600')
    root = args.root.resolve()
    out = (args.out or root / 'output' / '02_analisi_riflessi' / 'test_02').resolve()
    esegui(root, out, args.preview_width)


if __name__ == '__main__':
    main()