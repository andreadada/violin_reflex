"""FASE 2 / TEST 05C — Evidenze luminose a più scale.

Obiettivo: cercare possibili riflessi di Base, limitando i falsi positivi
causati da corde, bordi e ombre, senza regole sul colore del violino.
Input: Base.tif, quattro TIFF registrati, relative maschere di validità.
Output: quattro PNG diagnostici e osservazioni.md in test_05c/.
Fasi: mappe Top-hat/DoG; differenza multi-luce; penalità bordi/ombre;
       scelta di esempi a risoluzione nativa.
Risultato atteso: valutare se i candidati sono più plausibili del Test 05B.

NON corregge fotografie. Lo score non è probabilità di riflesso.
Eseguire dalla root: python code/phase2_reflection/2_reflection_step5c.py
Richiede 2_reflection_step5.py e 2_reflection_step5b.py nella stessa cartella.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import cv2
import numpy as np

SCALA = 8
RADII = (5, 15, 40)       # pixel nella mappa 1:8
DOG = ((3, 10), (10, 30), (25, 65))
SIGMA_GAIN = 32.0
SOGLIA = 0.10
CROP = 448


def importa(nome: str):
    """Carica i metodi diagnostici del Test 05 / 05B senza duplicarli."""
    path = Path(__file__).resolve().with_name(nome)
    if not path.is_file():
        raise FileNotFoundError(f'Script richiesto nella stessa cartella: {path}')
    spec = importlib.util.spec_from_file_location('diag_' + nome.replace('.', '_'), path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Impossibile caricare {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def blur_interno(lum: np.ndarray, support: np.ndarray, sigma: float) -> np.ndarray:
    """Sfoca usando solo pixel del soggetto: non trascina il fondo sui bordi."""
    w = support.astype(np.float32)
    num = cv2.GaussianBlur(lum * w, (0, 0), sigma)
    den = cv2.GaussianBlur(w, (0, 0), sigma)
    return num / np.maximum(den, 1e-5)


def risposte_multiscala(lum: np.ndarray, support: np.ndarray):
    """Top-hat per picchi luminosi; DoG per anomalie di più dimensioni.

    I valori vengono riscalati solo per costruire mappe esplorative.
    Top-hat e DoG non distinguono in modo certo riflessi e bordi chiari.
    """
    # Fuori dal soggetto usiamo un livello elevato per non produrre falsi
    # picchi su un contorno che confina con uno sfondo molto scuro.
    inside = lum[support]
    neutral = float(np.percentile(inside, 85)) if inside.size else 0.5
    filled = np.where(support, lum, neutral).astype(np.float32)
    hats = []
    for r in RADII:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*r+1, 2*r+1))
        opened = cv2.morphologyEx(filled, cv2.MORPH_OPEN, k)
        hats.append(np.clip((filled - opened - .009)/.13, 0, 1))
    dogs = []
    for small, large in DOG:
        detail = blur_interno(lum, support, small) - blur_interno(lum, support, large)
        dogs.append(np.clip((detail - .007)/.09, 0, 1))
    top = np.maximum.reduce(hats) * support
    dog = np.maximum.reduce(dogs) * support
    combined = np.maximum(top, dog)
    return top.astype(np.float32), dog.astype(np.float32), combined.astype(np.float32)


def gradiente(lum: np.ndarray, support: np.ndarray) -> np.ndarray:
    """Gradiente Sobel robusto; misura i bordi, non la presenza di riflessi."""
    sx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(sx, sy)
    samples = mag[support]
    ref = float(np.percentile(samples, 94)) if samples.size else 0.1
    return np.clip(mag / max(ref, .015), 0, 1)


def analizza(base_y: np.ndarray, donors_y: list[np.ndarray], validi: list[np.ndarray],
             support: np.ndarray, sigma_gain: float):
    """Combina evidenza multi-scala e differenze tra illuminazioni.

    Una maggiore luminosità di Base non basta: penalizziamo ombre ed edge
    persistenti che comparirebbero anche in assenza di riflessi.
    """
    _, _, evidence = risposte_multiscala(base_y, support)
    grads, gains, scores, differences = [], [], [], []
    grad_b = gradiente(base_y, support)
    for d, valid in zip(donors_y, validi):
        gain, _ = B.guadagno_lento(base_y, d, support & valid, sigma_gain)
        normalized = np.clip(d * gain, 0, 1)
        _, _, d_evidence = risposte_multiscala(normalized, support)
        grads.append(gradiente(normalized, support))
        gains.append(gain)
        # Differenza fotometrica e vantaggio nella mappa locale del donatore.
        diff = np.clip((base_y - normalized - .018)/.16, 0, 1)
        pattern = np.clip((evidence - d_evidence + .02)/.36, 0, 1)
        contrast = .65*diff + .35*pattern
        # Se il donatore è quasi nero o introduce un'ombra forte, niente prova.
        exposure = np.clip((d - .085)/.23, 0, 1)
        shadow = np.clip((normalized / np.maximum(base_y, .08) - .48)/.34, 0, 1)
        candidate = evidence * contrast * exposure * shadow * valid.astype(np.float32)
        scores.append(candidate)
        differences.append(contrast)
    # Contorni presenti in molte illuminazioni: soprattutto oggetto/corde.
    persistent = np.minimum(grad_b, np.median(np.stack(grads, axis=0), axis=0))
    edge_guard = 1 - .72*np.clip((persistent - .20)/.65, 0, 1)
    # Protezione morbida: NON eliminiamo i bordi (possono anch'essi riflettere).
    final = np.stack(scores, axis=0) * edge_guard[None, ...] * support[None, ...]
    return (evidence, edge_guard, np.stack(differences, axis=0),
            final, gains, persistent)


def esegui(root: Path, out: Path, threshold: float, sigma_gain: float, crop: int):
    """Genera diagnostiche senza toccare gli originali o i vecchi test."""
    root, out = root.resolve(), out.resolve()
    if out in (root, root/'images') or root/'images' in out.parents:
        raise ValueError('Output non consentito dentro images/ o nella root.')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Output già presente: {out}. Usa --out per un nuovo test.')
    paths, mpaths = A.percorsi(root)
    missing = [p for p in [*paths, *mpaths] if not p.is_file()]
    if missing:
        raise FileNotFoundError('File di input mancanti:\n'+'\n'.join(map(str,missing)))
    raw = [A.leggi_rgb(p) for p in paths]
    h, w = raw[0].shape[:2]
    if any(x.shape != (h,w,3) or x.dtype != np.uint8 for x in raw):
        raise ValueError('Tutti i TIFF devono essere RGB uint8 e avere le stesse dimensioni.')
    sw, sh = max(1, round(w/SCALA)), max(1, round(h/SCALA))
    preview = [A.anteprima(x, sw, sh) for x in raw]
    validi = []
    for p in mpaths:
        m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if m is None or m.shape != (h,w):
            raise ValueError(f'Maschera di validità errata: {p}')
        validi.append(cv2.resize(m,(sw,sh),interpolation=cv2.INTER_NEAREST)>0)
    support, estimated = A.area_soggetto(preview[0])
    ys = [B.luminanza(p) for p in preview]
    top, dog, base_evidence = risposte_multiscala(ys[0], support)
    evidence, edge_guard, differences, stack, gains, persistence = analizza(
        ys[0], ys[1:], validi, support, sigma_gain)
    best = np.argmax(stack, axis=0)
    score = np.max(stack, axis=0)
    candidate = (score >= threshold) & support
    count = int(np.count_nonzero(candidate))
    out.mkdir(parents=True, exist_ok=True)
    def panel(panels):
        return np.hstack([A.aggiungi_titolo(img, label) for img,label in panels])
    A.salva_png(out/'01_risposte_multiscala.png',panel([
        (preview[0],'Base'),(B.pseudo_colore(top,support),'Top-hat multi-scala'),
        (B.pseudo_colore(dog,support),'DoG multi-scala')]))
    diff = np.max(differences, axis=0)
    A.salva_png(out/'02_confronto_illuminazioni.png',panel([
        (B.pseudo_colore(base_evidence,support),'Anomalia in Base'),
        (B.pseudo_colore(diff,support),'Differenza multi-luce'),
        (B.pseudo_colore(1-edge_guard,support),'Bordi persistenti (penalita)')]))
    selected = preview[0].copy()
    colors = np.array([[34,123,202],[242,157,63],[51,177,111],[172,102,206]],np.uint8)
    selected[candidate] = np.uint8(.25*selected[candidate]+.75*colors[best[candidate]])
    A.salva_png(out/'03_candidati_e_donatori.png',panel([
        (B.overlay(preview[0],score,candidate),'Candidati 05C'),
        (selected,'R1 blu / R2 arancio / R3 verde / R4 viola'),
        (B.pseudo_colore(score,support),'Score (non probabilita)')]))
    centers = B.scegli_centri(score,support,threshold,crop,SCALA)
    stats = B.crea_confronti(raw[0],raw[1:],score,gains,best,centers,SCALA,crop,A.salva_png,out)
    temp = out/'03_confronti_nativi.png'
    if temp.exists():
        temp.rename(out/'04_confronti_nativi.png')
    distribution = [int(np.count_nonzero(candidate & (best==i))) for i in range(4)]
    lines = ['# Fase 2 — Test 05C (solo diagnostica)', '',
             f'- Mappe: {sw} × {sh} (1:{SCALA}); TIFF: {w} × {h} RGB uint8.',
             f'- Supporto non cromatico stimato: {estimated}; copertura {100*np.mean(support):.1f}%.',
             f'- Top-hat raggi mappa: {RADII}; DoG sigma mappa: {DOG}.',
             f'- Soglia score: {threshold:.3f}; sigma bilanciamento: {sigma_gain:.1f}.',
             f'- Candidati: {count} pixel mappa ({100*np.mean(candidate):.2f}% del frame).',
             f'- Scelte R1–R4: {distribution}.', '',
             '## Ritagli nativi',
             '| Zona | Centro | R | Score | Guadagno | Microcontrasto Base → R |',
             '| --- | --- | --- | ---: | ---: | --- |']
    for s in stats:
        lines.append(f"| {s['zona']} | {s['center']} | R{s['donor']} | {s['score']:.3f} | {s['gain']:.2f} | {s['detail_base']:.4f} → {s['detail_donor']:.4f} |")
    lines.extend(['', '## Verifica manuale richiesta',
                  '- Il riflesso ampio della parte alta destra appare più chiaramente?',
                  '- Corde, ponticello, bordi e tavola colori sono ancora selezionati?',
                  '- I donatori mostrano tessitura recuperata o solo ombre/rumore?',
                  '- La maschera include il soggetto corretto? Non è segmentazione universale.',
                  '', '## Limiti',
                  '- Top-hat/DoG segnalano anomalie luminose, non riflessi certificati.',
                  '- La penalità dei bordi è morbida: veri riflessi sul bordo non sono esclusi.',
                  '- Normalizzazione, soglia e scale sono euristiche: foto TIFF non sono RAW radiometrici.',
                  '- Lo score non è una probabilità e i candidati non sono ground truth.',
                  '- Nessuna modifica ai TIFF. Test 02 rimane la baseline fotografica.',
                  '', '## Decisione', '', 'Da prendere dopo valutazione dei PNG reali.'])
    (out/'osservazioni.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for f in sorted(out.iterdir()):
        print('Creato:',f)
    print('Candidati diagnostici:',count)


def main():
    p = argparse.ArgumentParser(description='Test 05C: multi-scala e confronto illuminazioni (solo diagnostica)')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--out',type=Path,default=None,help='Cartella nuova, default test_05c')
    p.add_argument('--threshold',type=float,default=SOGLIA)
    p.add_argument('--gain-sigma',type=float,default=SIGMA_GAIN)
    p.add_argument('--crop',type=int,default=CROP)
    args=p.parse_args()
    if not .01<=args.threshold<=1 or not 4<=args.gain_sigma<=120 or not 128<=args.crop<=1024:
        p.error('Parametri: threshold .01..1; gain-sigma 4..120; crop 128..1024')
    root=args.root.resolve()
    out=(args.out or root/'output'/'02_analisi_riflessi'/'test_05c').resolve()
    esegui(root,out,args.threshold,args.gain_sigma,args.crop)


if __name__=='__main__':
    A=importa('2_reflection_step5.py')
    B=importa('2_reflection_step5b.py')
    main()
