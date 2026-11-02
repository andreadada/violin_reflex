"""FASE 2 / STEP 1 — Confronto fotografico delle cinque illuminazioni.

Esecuzione dalla radice di ViolinReflectionRemoval:
    python 2_reflection_step1.py
    python 2_reflection_step1.py --roi 2200 3000 600 600

Nessuna correzione, fusione o modifica ai TIFF. Il ritaglio --roi è facoltativo:
coordinate X Y LARGHEZZA ALTEZZA nella Base, in pixel originali.
Dipendenze: numpy, opencv-python, tifffile (come la Fase 1).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile


NOMI = ["Base", "Riflesso_1", "Riflesso_2", "Riflesso_3", "Riflesso_4"]
ETICHETTE = ["BASE - 4 luci"] + [f"RIFLESSO {i} - luce {i}" for i in range(1, 5)]


def file_immagini(root: Path) -> list[Path]:
    registrate = root / "output" / "01_registrazione" / "test_01" / "risultato" / "registered"
    return [root / "images" / "Base.tif"] + [
        registrate / f"Riflesso_{i}_registered.tif" for i in range(1, 5)
    ]


def caratteristiche(path: Path) -> tuple[tuple[int, int, int], np.dtype]:
    with tifffile.TiffFile(path) as tf:
        serie = tf.series[0]
        forma = tuple(serie.shape)
        tipo = np.dtype(serie.dtype)
    if len(forma) != 3 or forma[2] != 3 or tipo not in (np.dtype("uint8"), np.dtype("uint16")):
        raise ValueError(f"TIFF RGB non supportato: {path} ({forma}, {tipo})")
    return forma, tipo


def leggi_rgb(path: Path) -> np.ndarray:
    """Memmap se possibile; altrimenti lettura normale. Nessun ridimensionamento."""
    try:
        return tifffile.memmap(path)
    except (OSError, ValueError, TypeError):
        return tifffile.imread(path)


def anteprima_rgb(rgb: np.ndarray, larghezza: int) -> np.ndarray:
    """Converte solo l'anteprima a 8 bit, senza normalizzare luminosità e colore."""
    h, w = rgb.shape[:2]
    if rgb.dtype == np.uint16:
        preview = (rgb >> 8).astype(np.uint8)
    else:
        preview = rgb
    nuova_altezza = max(1, round(h * larghezza / w))
    return cv2.resize(preview, (larghezza, nuova_altezza), interpolation=cv2.INTER_AREA)


def pannello(rgb8: np.ndarray, etichetta: str) -> np.ndarray:
    """Crea un pannello BGR con etichetta; i pixel della fotografia non cambiano."""
    immagine = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    header = np.full((48, immagine.shape[1], 3), 28, dtype=np.uint8)
    cv2.putText(header, etichetta, (12, 31), cv2.FONT_HERSHEY_SIMPLEX,
                0.57, (250, 250, 250), 1, cv2.LINE_AA)
    return cv2.vconcat([header, immagine])


def salva_png(path: Path, image_bgr: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image_bgr):
        raise OSError(f"Impossibile scrivere: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fase 2: confronto visivo, senza modificare i TIFF")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent,
                        help="Cartella ViolinReflectionRemoval (default: cartella dello script)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Directory di output; default: output/02_analisi_riflessi/test_01")
    parser.add_argument("--roi", type=int, nargs=4, metavar=("X", "Y", "L", "H"),
                        help="Ritaglio comune alle 5 immagini a pixel nativi")
    parser.add_argument("--preview-width", type=int, default=520,
                        help="Larghezza di ciascuna anteprima in pixel (default 520)")
    args = parser.parse_args()

    root = args.root.resolve()
    out = (args.out or root / "output" / "02_analisi_riflessi" / "test_01").resolve()
    images_dir = root / "images"
    if out == root or out == images_dir or images_dir in out.parents:
        parser.error("La directory di output non può essere images/ o la radice del progetto")
    if not 200 <= args.preview_width <= 1400:
        parser.error("--preview-width deve essere compreso tra 200 e 1400")

    sorgenti = file_immagini(root)
    mancanti = [str(p) for p in sorgenti if not p.is_file()]
    if mancanti:
        parser.error("Immagini mancanti:\n  " + "\n  ".join(mancanti))

    forma, tipo = caratteristiche(sorgenti[0])
    for p in sorgenti[1:]:
        if caratteristiche(p) != (forma, tipo):
            parser.error(f"Dimensioni o tipo differenti da Base: {p}")
    h, w, _ = forma

    roi = args.roi
    if roi:
        x, y, larghezza, altezza = roi
        if x < 0 or y < 0 or larghezza < 1 or altezza < 1 or x + larghezza > w or y + altezza > h:
            parser.error(f"ROI non valida per immagini {w} x {h}: {roi}")

    out.mkdir(parents=True, exist_ok=True)
    panorama_path = out / "01_confronto_illuminazioni.png"
    roi_path = out / (f"02_roi_{x}_{y}_{larghezza}_{altezza}.png" if roi else "")

    # Non riscriviamo output già esistenti: eseguire in un altro test_NN se necessario.
    if not panorama_path.exists():
        pannelli = []
        for path, etichetta in zip(sorgenti, ETICHETTE):
            immagine = leggi_rgb(path)
            pannelli.append(pannello(anteprima_rgb(immagine, args.preview_width), etichetta))
            del immagine
        salva_png(panorama_path, cv2.hconcat(pannelli))
        print("Panoramica:", panorama_path)
    else:
        print("Panoramica già presente (non sovrascritta):", panorama_path)

    if roi:
        if roi_path.exists():
            print("Ritaglio già presente (non sovrascritto):", roi_path)
        else:
            pannelli = []
            for path, etichetta in zip(sorgenti, ETICHETTE):
                immagine = leggi_rgb(path)
                ritaglio = immagine[y:y + altezza, x:x + larghezza]
                # Solo il pannello: nessun resize, un pixel sorgente = un pixel output.
                pannelli.append(pannello(anteprima_rgb(ritaglio, larghezza), etichetta))
                del immagine
            salva_png(roi_path, cv2.hconcat(pannelli))
            print("Ritaglio 100% (senza ridimensionamento):", roi_path)

    note = out / "osservazioni.md"
    if not note.exists():
        note.write_text(
            "# Fase 2 / Test 01 — Confronto delle illuminazioni\n\n"
            f"Dimensioni sorgenti: {w} × {h} px; tipo RGB: {tipo}.\n\n"
            "## Osservazioni visive\n\n"
            "- Zona da migliorare: da individuare sulla fotografia originale.\n"
            "- Scatto con riflesso meno fastidioso: da verificare.\n"
            "- Dettagli e colore preservati: da verificare.\n\n"
            "## Conclusione\n\n"
            "Confronto fotografico, nessuna correzione applicata.\n",
            encoding="utf-8",
        )
    print("Note:", note)
    print("Nessun TIFF originale o registrato è stato modificato.")


if __name__ == "__main__":
    main()