"""FASE 1 — Studio esplorativo della registrazione.

SCHEDA DEL FILE (riferita al progetto locale)
Obiettivo: Esplorare progressivamente il confronto geometrico tra Base e gli scatti illuminati separatamente.
Input: images/Base.tif e images/Riflesso_1.tif ... Riflesso_4.tif.
Output: PNG e CSV in output/allineamento/ (esperimenti storici).
Fasi: Ritagli di controllo; gradienti Sobel; confronto dei contorni; stime di spostamento.
Risultato atteso: Diagnostiche per comprendere il disallineamento, non TIFF corretti.
Nota: Script storico con istruzioni eseguite direttamente: eseguirlo soltanto per ripetere quelle prove.
"""


from pathlib import Path

import cv2
import numpy as np

# ==========================================
# STEP 1.1 - CONFRONTO DELLE 4 FOTOGRAFIE
# ==========================================

# 1. Prepariamo i percorsi.
CARTELLA = Path(__file__).resolve().parents[2]
IMMAGINI = CARTELLA / "images"
OUTPUT = CARTELLA / "output" / "allineamento"

OUTPUT.mkdir(parents=True, exist_ok=True)

# 2. Carichiamo Base in scala di grigi.
# Sarà il riferimento per tutti i confronti.
base = cv2.imread(
    str(IMMAGINI / "Base.tif"),
    cv2.IMREAD_GRAYSCALE
)

if base is None:
    raise RuntimeError("Non riesco a leggere Base.tif")

altezza, larghezza = base.shape

print("Dimensioni Base:", base.shape)

# 3. Selezioniamo un punto sulla tavola colori.
# Le coordinate sono percentuali della fotografia.
cx = int(larghezza * 0.32)
cy = int(altezza * 0.915)

# Ritaglio di 640 x 640 pixel originali.
lato = 640
meta = lato // 2

x0, x1 = cx - meta, cx + meta
y0, y1 = cy - meta, cy + meta

# 4. Ritaglio della fotografia Base.
crop_base = base[y0:y1, x0:x1]


# ==========================================
# STEP 2 - RILEVAMENTO DEI CONTORNI
# ==========================================

def sobel(immagine):
    """Calcola l'intensità dei contorni tramite gradienti Sobel, utile al confronto geometrico."""

    # 1. Riduciamo leggermente il rumore.
    # Il filtro agisce soltanto sul ritaglio usato per l'analisi.
    sfocata = cv2.GaussianBlur(
        immagine, (3, 3), 0.5
    )

    # 2. Convertiamo i pixel in float32.
    # Le derivate possono avere valori negativi,
    # che il formato uint8 non potrebbe rappresentare.
    img_float = sfocata.astype(np.float32)

    # 3. Calcoliamo il gradiente orizzontale.
    grad_x = cv2.Sobel(
        img_float, cv2.CV_32F,
        1, 0, ksize=3
    )

    # 4. Calcoliamo il gradiente verticale.
    grad_y = cv2.Sobel(
        img_float, cv2.CV_32F,
        0, 1, ksize=3
    )

    # 5. Combiniamo le due derivate.
    # Il risultato misura l'intensità di ogni contorno.
    intensita_bordi = cv2.magnitude(
        grad_x, grad_y
    )

    return intensita_bordi


# Calcoliamo Sobel su Base una sola volta,
# perché sarà il riferimento per tutti i confronti.
bordi_base = sobel(crop_base)

# Lista in cui raccoglieremo i quattro nuovi overlay.
overlays_sobel = []



overlays = []


# ==========================================
# STEP 4 - ANALISI DI PIU' ZONE
# ==========================================

# Ogni coppia rappresenta la posizione del centro
# di un ritaglio rispetto a larghezza e altezza.
ZONE = {
    "alto_sx": (0.30, 0.17),
    "alto_dx": (0.70, 0.17),
    "centro_sx": (0.35, 0.43),
    "centro_dx": (0.65, 0.43),
    "basso_sx": (0.32, 0.70),
    "basso_dx": (0.68, 0.70),
    "tavola_sx": (0.32, 0.915),
    "tavola_dx": (0.69, 0.915),
}

# Qui raccogliamo le misurazioni di tutte le foto.
risultati_step4 = []


# 5. Ripetiamo il confronto per tutte le fotografie.
for numero in range(1, 5):



    nome = f"Riflesso_{numero}"

    print(f"\nSto confrontando Base con {nome}")

    # Carichiamo la fotografia corrente.
    riflesso = cv2.imread(
        str(IMMAGINI / f"{nome}.tif"),
        cv2.IMREAD_GRAYSCALE
    )

    if riflesso is None:
        raise RuntimeError(f"Impossibile leggere {nome}.tif")

    # Devono avere le stesse dimensioni.
    if riflesso.shape != base.shape:
        raise ValueError(f"Dimensioni diverse: {nome}")

    # 6. Estraiamo le stesse coordinate.
    crop_riflesso = riflesso[y0:y1, x0:x1]



    # ==========================================
    # STEP 2 - VISUALIZZAZIONE GAUSSIANA
    # ==========================================

    # Applichiamo lo stesso filtro gaussiano
    # che utilizziamo nella funzione sobel().
    gauss_base = cv2.GaussianBlur(
        crop_base, (3, 3), 0.5
    )

    gauss_riflesso = cv2.GaussianBlur(
        crop_riflesso, (3, 3), 0.5
    )

    # Creiamo un overlay rosso/ciano.
    # B e G = Riflesso_n; R = Base.
    overlay_gauss = cv2.merge([
        gauss_riflesso,
        gauss_riflesso,
        gauss_base
    ])

    # Salviamo il confronto gaussiano.
    cv2.imwrite(
        str(OUTPUT / f"step2_gaussian_{nome}.png"),
        overlay_gauss
    )


    # 7. Creiamo l'overlay BGR:
    # Blu  = Riflesso corrente
    # Verde = Riflesso corrente
    # Rosso = Base
    overlay = cv2.merge([
        crop_riflesso,
        crop_riflesso,
        crop_base
    ])

    # Scriviamo il nome sul pannello.
    cv2.putText(
        overlay,
        f"Base + {nome}",
        (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # ==========================================
    # LEGENDA COLORI
    # Rosso = Base
    # Ciano = Riflesso_n
    # ==========================================

    # Rettangolino rosso per Base
    cv2.rectangle(overlay, (15, 50), (35, 70), (0, 0, 255), -1)
    cv2.putText(
        overlay,
        "Base",
        (45, 67),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1
    )

    cv2.putText(
        overlay,
        "Grigio = simili",
        (15, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1
    )

    # Rettangolino ciano per Riflesso_n
    cv2.rectangle(overlay, (15, 80), (35, 100), (255, 255, 0), -1)
    cv2.putText(
        overlay,
        nome,
        (45, 97),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1
    )

    # Salviamo anche l'overlay individuale.
    cv2.imwrite(
        str(OUTPUT / f"step1_{nome}_overlay.png"),
        overlay
    )

    # Aggiungiamolo alla lista dei pannelli.
    overlays.append(overlay)


    # ==========================================
    # STEP 2 - CONFRONTO DEI CONTORNI
    # ==========================================

    # 1. Applichiamo Sobel al ritaglio corrente.
    bordi_riflesso = sobel(crop_riflesso)


    # ==========================================
    # STEP 3 - CORRELAZIONE DI FASE
    # ==========================================

    # Dimensioni dei ritagli che stiamo confrontando.
    h, w = bordi_base.shape

    # Finestra di Hanning:
    # attenua i bordi artificiali del ritaglio,
    # che potrebbero disturbare la trasformata di Fourier.
    finestra = cv2.createHanningWindow(
        (w, h),
        cv2.CV_32F
    )

    # Stimiamo lo spostamento fra i due insiemi di contorni.
    # La funzione restituisce:
    # (dx, dy) = traslazione della seconda immagine
    # risposta = intensità/coerenza del picco di correlazione.
    (dx, dy), risposta = cv2.phaseCorrelate(
        bordi_base,
        bordi_riflesso,
        finestra
    )

    # Stampiamo i valori nel terminale.
    print(
        f"{nome}: "
        f"dx={dx:+.3f} px, "
        f"dy={dy:+.3f} px, "
        f"risposta={risposta:.3f}"
    )


    # 2. Troviamo una scala comune per visualizzare
    # i gradienti delle due immagini.
    # Usiamo il percentile 99.5 per evitare che pochi
    # valori estremi rendano tutti i bordi troppo scuri.
    scala = max(
        np.percentile(bordi_base, 99.5),
        np.percentile(bordi_riflesso, 99.5),
        1.0
    )

    # 3. Convertiamo i gradienti in immagini 0-255
    # esclusivamente per visualizzarli e salvarli.
    base_vis = np.uint8(
        np.clip(bordi_base / scala * 255, 0, 255)
    )

    riflesso_vis = np.uint8(
        np.clip(bordi_riflesso / scala * 255, 0, 255)
    )

    # 4. Costruiamo un nuovo overlay, questa volta
    # usando i CONTORNI anziché i pixel originali.
    #
    # B = contorni Riflesso_n
    # G = contorni Riflesso_n
    # R = contorni Base
    overlay_sobel = cv2.merge([
        riflesso_vis,
        riflesso_vis,
        base_vis
    ])


    # ==========================================
    # STEP 3 - VERIFICA VISIVA
    # ==========================================

    # Matrice di traslazione:
    # compensiamo lo spostamento misurato.
    M = np.float32([
        [1, 0, -dx],
        [0, 1, -dy]
    ])

    # Spostiamo soltanto i contorni del ritaglio.
    # I TIFF originali NON vengono modificati.
    riflesso_corretto = cv2.warpAffine(
        riflesso_vis,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )

    # Prima: contorni nelle posizioni originali.
    prima = overlay_sobel.copy()

    # Dopo: contorni Riflesso_n traslati,
    # contorni Base sempre fermi.
    dopo = cv2.merge([
        riflesso_corretto,
        riflesso_corretto,
        base_vis
    ])

    # Creiamo un'intestazione per ogni immagine.
    cv2.rectangle(prima, (0, 0), (w, 38), (20, 20, 20), -1)
    cv2.rectangle(dopo, (0, 0), (w, 38), (20, 20, 20), -1)

    cv2.putText(
        prima, "PRIMA",
        (15, 27), cv2.FONT_HERSHEY_SIMPLEX,
        0.75, (255, 255, 255), 2
    )

    cv2.putText(
        dopo, f"DOPO: dx={dx:+.2f}, dy={dy:+.2f}",
        (15, 27), cv2.FONT_HERSHEY_SIMPLEX,
        0.65, (255, 255, 255), 2
    )

    # Affianchiamo il prima e il dopo.
    confronto_step3 = cv2.hconcat([prima, dopo])

    # Salviamo il risultato.
    cv2.imwrite(
        str(OUTPUT / f"step3_prima_dopo_{nome}.png"),
        confronto_step3
    )


    # 5. Aggiungiamo titolo e legenda.
    cv2.putText(
        overlay_sobel,
        f"Sobel: Base + {nome}",
        (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8, (255, 255, 255), 2
    )

    # Rosso = contorni di Base.
    cv2.rectangle(
        overlay_sobel,
        (15, 50), (35, 70),
        (0, 0, 255), -1
    )
    cv2.putText(
        overlay_sobel, "Base",
        (45, 67),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55, (255, 255, 255), 1
    )

    # Ciano = contorni del riflesso corrente.
    cv2.rectangle(
        overlay_sobel,
        (15, 80), (35, 100),
        (255, 255, 0), -1
    )
    cv2.putText(
        overlay_sobel, nome,
        (45, 97),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55, (255, 255, 255), 1
    )

    # 6. Salviamo separatamente i contorni.
    cv2.imwrite(
        str(OUTPUT / "step2_sobel_Base.png"),
        base_vis
    )

    cv2.imwrite(
        str(OUTPUT / f"step2_sobel_{nome}.png"),
        riflesso_vis
    )

    # 7. Salviamo l'overlay individuale.
    cv2.imwrite(
        str(OUTPUT / f"step2_overlay_{nome}.png"),
        overlay_sobel
    )

    # 8. Lo conserviamo per il confronto finale 2x2.
    overlays_sobel.append(overlay_sobel)

    # ==========================================
    # STEP 4 - MISURAZIONI LOCALI
    # ==========================================

    print(f"\n--- STEP 4: {nome} ---")

    misure = []

    # Anteprima ridotta SOLO per mostrare le zone.
    # Le misurazioni continueranno a usare i pixel originali.
    anteprima = cv2.resize(
        base,
        (larghezza // 8, altezza // 8),
        interpolation=cv2.INTER_AREA
    )
    anteprima = cv2.cvtColor(
        anteprima, cv2.COLOR_GRAY2BGR
    )

    for zona, (xr, yr) in ZONE.items():
        # Calcoliamo il centro in pixel originali.
        cx_z = round(xr * larghezza)
        cy_z = round(yr * altezza)

        # Estraiamo 640x640 pixel ORIGINALI.
        x_inizio = cx_z - lato // 2
        y_inizio = cy_z - lato // 2

        a = base[
            y_inizio:y_inizio + lato,
            x_inizio:x_inizio + lato
        ]
        b = riflesso[
            y_inizio:y_inizio + lato,
            x_inizio:x_inizio + lato
        ]

        # Calcoliamo i contorni Sobel.
        ga = sobel(a)
        gb = sobel(b)

        # Prepariamo la finestra di Hanning.
        finestra_z = cv2.createHanningWindow(
            (lato, lato), cv2.CV_32F
        )

        # Stimiamo la traslazione della zona corrente.
        (dx_z, dy_z), q = cv2.phaseCorrelate(
            ga, gb, finestra_z
        )

        misure.append((dx_z, dy_z, q))
        risultati_step4.append([
            nome, zona, dx_z, dy_z, q
        ])

        print(
            f"{zona:12s} "
            f"dx={dx_z:+7.2f} "
            f"dy={dy_z:+7.2f} "
            f"qualita={q:.3f}"
        )

        # Disegniamo la zona sull'anteprima.
        # Verde = risposta >= 0.20
        # Arancione = risposta inferiore a 0.20
        colore = (
            (50, 210, 50) if q >= 0.20
            else (0, 170, 255)
        )

        px = round(cx_z / 8)
        py = round(cy_z / 8)
        r = lato // 16

        cv2.rectangle(
            anteprima,
            (px - r, py - r),
            (px + r, py + r),
            colore, 2
        )

        cv2.putText(
            anteprima,
            f"{zona}: {dx_z:+.1f}, {dy_z:+.1f}",
            (px - r, py - r - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43, colore, 1, cv2.LINE_AA
        )

    # Consideriamo soltanto le misure
    # con risposta di correlazione sufficiente.
    affidabili = np.array([
        [dx_z, dy_z]
        for dx_z, dy_z, q in misure
        if q >= 0.20
           and np.isfinite(dx_z)
           and np.isfinite(dy_z)
    ]).reshape(-1, 2)

    if len(affidabili) < 3:
        print("ESITO: non conclusivo.")
    else:
        # La mediana è meno sensibile ai valori anomali.
        mediana = np.median(affidabili, axis=0)

        # Distanza di ogni misura dalla mediana.
        scarti = np.linalg.norm(
            affidabili - mediana, axis=1
        )

        # Escludiamo risultati distanti oltre 2 pixel.
        coerenti = affidabili[scarti <= 2.0]

        if len(coerenti) < 3:
            print("ESITO: misure discordanti.")
        else:
            dx_finale, dy_finale = np.median(
                coerenti, axis=0
            )

            dispersione = np.median(
                np.linalg.norm(
                    coerenti - [dx_finale, dy_finale],
                    axis=1
                )
            )

            print(
                f"MEDIANA: dx={dx_finale:+.2f}, "
                f"dy={dy_finale:+.2f}, "
                f"dispersione={dispersione:.2f}"
            )

            if (
                    dispersione > 0.50
                    or len(coerenti) <= len(affidabili) // 2
            ):
                print("ESITO: da verificare, misure non abbastanza coerenti.")
            else:
                print("ESITO: traslazione globale plausibile.")

    # Salviamo la mappa diagnostica delle otto zone.
    cv2.imwrite(
        str(OUTPUT / f"step4_zone_{nome}.png"),
        anteprima
    )

    del riflesso



# 8. Componiamo quattro pannelli in una griglia 2x2.
# hconcat = affianca orizzontalmente.
# vconcat = impila verticalmente.

riga_superiore = cv2.hconcat([
    overlays[0],
    overlays[1]
])

riga_inferiore = cv2.hconcat([
    overlays[2],
    overlays[3]
])

confronto_finale = cv2.vconcat([
    riga_superiore,
    riga_inferiore
])

# 9. Salviamo il risultato complessivo.
percorso_finale = OUTPUT / "step1_tutti_overlay.png"

cv2.imwrite(
    str(percorso_finale),
    confronto_finale
)

print("\nSTEP 1.1 completato!")
print("Risultato:", percorso_finale)



# ==========================================
# STEP 2 - RISULTATO FINALE
# ==========================================

# Prima riga: confronti con Riflesso_1 e Riflesso_2.
riga1 = cv2.hconcat([
    overlays_sobel[0],
    overlays_sobel[1]
])

# Seconda riga: confronti con Riflesso_3 e Riflesso_4.
riga2 = cv2.hconcat([
    overlays_sobel[2],
    overlays_sobel[3]
])

# Uniamo verticalmente le due righe.
confronto_sobel = cv2.vconcat([
    riga1,
    riga2
])

# Salviamo la griglia da 1280 x 1280 pixel.
percorso_sobel = OUTPUT / "step2_tutti_overlay_sobel.png"

cv2.imwrite(
    str(percorso_sobel),
    confronto_sobel
)

print("\nSTEP 2 completato!")
print("Risultato Sobel:", percorso_sobel)


# ==========================================
# STEP 4 - ESPORTAZIONE CSV
# ==========================================

import csv

percorso_csv = OUTPUT / "step4_misure.csv"

with open(percorso_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        "fotografia",
        "zona",
        "dx",
        "dy",
        "qualita"
    ])

    writer.writerows(risultati_step4)

print("\nSTEP 4 completato!")
print("CSV salvato:", percorso_csv)


# ==========================================
# STEP 4.1 - RIEPILOGO VISIVO COMPLETO
# ==========================================

# Dimensioni di ogni pannello del riepilogo.
# Questi valori riguardano soltanto la visualizzazione.
LARGHEZZA_PANNELLO = 640
ALTEZZA_PANNELLO = 700


def crea_pannello(percorso, titolo):
    """
    Legge un'immagine diagnostica e la inserisce
    in un pannello con titolo.

    Mantiene le proporzioni dell'immagine originale.
    """

    immagine = cv2.imread(str(percorso))

    if immagine is None:
        raise FileNotFoundError(
            f"Immagine non trovata: {percorso}"
        )

    h, w = immagine.shape[:2]

    # Lasciamo 55 pixel in alto per il titolo.
    spazio_immagine = ALTEZZA_PANNELLO - 55

    # Calcoliamo quanto possiamo ridimensionare
    # l'immagine senza deformarne le proporzioni.
    scala = min(
        LARGHEZZA_PANNELLO / w,
        spazio_immagine / h
    )

    nuova_w = round(w * scala)
    nuova_h = round(h * scala)

    ridotta = cv2.resize(
        immagine,
        (nuova_w, nuova_h),
        interpolation=cv2.INTER_AREA
    )

    # Creiamo uno sfondo scuro.
    pannello = np.full(
        (ALTEZZA_PANNELLO, LARGHEZZA_PANNELLO, 3),
        25,
        dtype=np.uint8
    )

    # Centriamo l'immagine nello spazio disponibile.
    x = (LARGHEZZA_PANNELLO - nuova_w) // 2
    y = 55 + (spazio_immagine - nuova_h) // 2

    pannello[y:y + nuova_h, x:x + nuova_w] = ridotta

    # Titolo in alto.
    cv2.putText(
        pannello,
        titolo,
        (15, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    return pannello


# Ogni elemento descrive una riga della griglia.
# {} verrà sostituito con Riflesso_1, Riflesso_2, ecc.
SEZIONI = [
    ("Overlay originale", "step1_{}_overlay.png"),
    ("Gaussian Blur", "step2_gaussian_{}.png"),
    ("Sobel", "step2_overlay_{}.png"),
    ("Prima / Dopo", "step3_prima_dopo_{}.png"),
    ("Otto zone", "step4_zone_{}.png"),
]

righe_griglia = []

# Per ogni elaborazione creiamo una riga di 4 foto.
for nome_step, modello_file in SEZIONI:

    pannelli = []

    for numero in range(1, 5):
        nome_foto = f"Riflesso_{numero}"

        # Ricaviamo il nome del PNG da leggere.
        nome_file = modello_file.format(nome_foto)

        pannello = crea_pannello(
            OUTPUT / nome_file,
            f"{nome_step} - {nome_foto}"
        )

        pannelli.append(pannello)

    # Affianchiamo i quattro pannelli.
    riga = cv2.hconcat(pannelli)

    righe_griglia.append(riga)


# Uniamo verticalmente tutte le righe.
griglia = cv2.vconcat(righe_griglia)

# Creiamo una fascia superiore dedicata alle legende.
larghezza_totale = griglia.shape[1]

intestazione = np.full(
    (125, larghezza_totale, 3),
    30,
    dtype=np.uint8
)

cv2.putText(
    intestazione,
    "VERIFICA ALLINEAMENTO - BASE vs 4 FOTOGRAFIE",
    (25, 35),
    cv2.FONT_HERSHEY_SIMPLEX,
    1.0,
    (255, 255, 255),
    2,
    cv2.LINE_AA
)

# Legenda rosso = Base.
cv2.rectangle(
    intestazione, (25, 60), (50, 85),
    (0, 0, 255), -1
)
cv2.putText(
    intestazione, "Rosso = Base",
    (60, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65, (255, 255, 255), 2
)

# Legenda ciano = Riflesso.
cv2.rectangle(
    intestazione, (320, 60), (345, 85),
    (255, 255, 0), -1
)
cv2.putText(
    intestazione, "Ciano = Riflesso_n",
    (355, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65, (255, 255, 255), 2
)

# Legenda grigio.
cv2.putText(
    intestazione, "Grigio = intensita simili",
    (740, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65, (255, 255, 255), 2
)

# Legenda verde = risposta >= 0.20.
cv2.rectangle(
    intestazione, (1220, 60), (1245, 85),
    (50, 210, 50), -1
)
cv2.putText(
    intestazione, "Verde = risposta >= 0.20",
    (1255, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65, (255, 255, 255), 2
)

# Legenda arancione = risposta < 0.20.
cv2.rectangle(
    intestazione, (1760, 60), (1785, 85),
    (0, 170, 255), -1
)
cv2.putText(
    intestazione, "Arancione = risposta < 0.20",
    (1795, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65, (255, 255, 255), 2
)

# Mettiamo intestazione e griglia una sotto l'altra.
risultato_completo = cv2.vconcat([
    intestazione,
    griglia
])

# Salviamo il PNG finale.
percorso_riepilogo = (
    OUTPUT / "step4_riepilogo_completo.png"
)

cv2.imwrite(
    str(percorso_riepilogo),
    risultato_completo
)

print("\nRIEPILOGO COMPLETO SALVATO!")
print("Percorso:", percorso_riepilogo)


# ==========================================
# STEP 5 - VERIFICA INDIPENDENTE SU VIOLINO
# Inserisci questo blocco ALLA FINE di allineamento.py
# ==========================================

# 1. Raccogliamo le misure gia' calcolate nello Step 4.
# La chiave e' (nome fotografia, nome zona).
misure_per_zona = {
    (foto, zona): (float(dx), float(dy), float(q))
    for foto, zona, dx, dy, q in risultati_step4
}

# La traslazione viene stimata SOLO dalla tavola colori.
ZONE_CALIBRAZIONE = ("tavola_sx", "tavola_dx")

# Queste zone del violino NON partecipano alla stima:
# servono per controllare se la correzione funziona anche altrove.
ZONE_VERIFICA = ("alto_sx", "centro_sx", "centro_dx", "basso_dx")

# Stessa finestra e stessi pixel nativi degli step precedenti.
finestra_5 = cv2.createHanningWindow((lato, lato), cv2.CV_32F)
righe_step5 = []
anteprime_step5 = []


def correlazione_contorni(g1, g2):
    """Somiglianza dei gradienti; escludiamo 24 px ai bordi del crop."""
    a = g1[24:-24, 24:-24].astype(np.float32).ravel()
    b = g2[24:-24, 24:-24].astype(np.float32).ravel()
    a -= a.mean()
    b -= b.mean()
    denominatore = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominatore) if denominatore > 1e-8 else 0.0


for numero in range(1, 5):
    nome = f"Riflesso_{numero}"

    # 2. Recuperiamo le due traslazioni della tavola colori.
    stime = []
    for zona in ZONE_CALIBRAZIONE:
        dx, dy, q = misure_per_zona[(nome, zona)]
        if q >= 0.20 and np.isfinite(dx) and np.isfinite(dy):
            stime.append((dx, dy))

    if len(stime) != 2:
        print(f"{nome}: tavola colori non affidabile: correzione saltata")
        continue

    # Se le due zone della tavola non concordano, NON applichiamo la traslazione.
    if np.linalg.norm(np.subtract(stime[0], stime[1])) > 2.0:
        print(f"{nome}: zone tavola discordanti: correzione saltata")
        continue

    dx_glob, dy_glob = np.median(np.array(stime), axis=0)
    print(f"\n{nome}: spostamento tavola dx={dx_glob:+.2f}, dy={dy_glob:+.2f}")

    # 3. Carichiamo una fotografia per volta, sempre a risoluzione originale.
    foto = cv2.imread(str(IMMAGINI / f"{nome}.tif"), cv2.IMREAD_GRAYSCALE)
    if foto is None or foto.shape != base.shape:
        raise RuntimeError(f"Impossibile leggere correttamente {nome}.tif")

    # La matrice sposta il ritaglio nella direzione OPPOSTA al disallineamento.
    M = np.float32([[1, 0, -dx_glob], [0, 1, -dy_glob]])
    pannelli = []

    for zona in ZONE_VERIFICA:
        xr, yr = ZONE[zona]
        cx_z, cy_z = round(xr * larghezza), round(yr * altezza)
        x0_z, y0_z = cx_z - lato // 2, cy_z - lato // 2

        a = base[y0_z:y0_z + lato, x0_z:x0_z + lato]
        b = foto[y0_z:y0_z + lato, x0_z:x0_z + lato]

        # Solo a fini diagnostici: non sovrascriviamo alcun TIFF originale.
        b_corretto = cv2.warpAffine(
            b, M, (lato, lato), flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101
        )

        ga, gb, gc = sobel(a), sobel(b), sobel(b_corretto)
        (dx_prima, dy_prima), q_prima = cv2.phaseCorrelate(ga, gb, finestra_5)
        (dx_dopo, dy_dopo), q_dopo = cv2.phaseCorrelate(ga, gc, finestra_5)
        sim_prima = correlazione_contorni(ga, gb)
        sim_dopo = correlazione_contorni(ga, gc)

        righe_step5.append([
            nome, zona, dx_glob, dy_glob,
            dx_prima, dy_prima, q_prima,
            dx_dopo, dy_dopo, q_dopo,
            sim_prima, sim_dopo
        ])

        print(f"  {zona:12s} residuo: "
              f"prima=({dx_prima:+.2f},{dy_prima:+.2f}) "
              f"dopo=({dx_dopo:+.2f},{dy_dopo:+.2f}) "
              f"similarita={sim_prima:.3f}->{sim_dopo:.3f}")

        # Stessa scala di visualizzazione prima/dopo.
        scala = max(float(np.percentile(g, 99.5)) for g in (ga, gb, gc))
        scala = max(scala, 1.0)
        def vis(g):
            return np.uint8(np.clip(g * (255.0 / scala), 0, 255))

        riferimento, prima, dopo = vis(ga), vis(gb), vis(gc)
        prima_rgb = cv2.merge([prima, prima, riferimento])
        dopo_rgb = cv2.merge([dopo, dopo, riferimento])

        # Legenda dentro le immagini: rosso Base, ciano Riflesso.
        for immagine, testo in (
            (prima_rgb, f"{zona} PRIMA  dx={dx_prima:+.1f} dy={dy_prima:+.1f}"),
            (dopo_rgb, f"{zona} DOPO  dx={dx_dopo:+.1f} dy={dy_dopo:+.1f}"),
        ):
            cv2.rectangle(immagine, (0, 0), (lato, 52), (25, 25, 25), -1)            cv2.putText(immagine, testo, (10, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.57, (255, 255, 255), 1)
            cv2.putText(immagine, "Rosso: Base  |  Ciano: Riflesso", (10, 43),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

        pannelli.append(cv2.hconcat([prima_rgb, dopo_rgb]))

    # 4. Un file dettagliato per fotografia: i crop hanno ancora pixel nativi.
    dettaglio = cv2.vconcat(pannelli)
    cv2.imwrite(str(OUTPUT / f"step5_verifica_{nome}.png"), dettaglio)

    # Per la GRIGLIA GENERALE riduciamo la sola anteprima del 50%.
    anteprime_step5.append(cv2.resize(
        dettaglio, (dettaglio.shape[1] // 2, dettaglio.shape[0] // 2),
        interpolation=cv2.INTER_AREA
    ))
    del foto

# 5. Griglia generale e CSV con i risultati delle zone NON usate per calibrare.
if anteprime_step5:
    cv2.imwrite(
        str(OUTPUT / "step5_tutte_le_verifiche.png"),
        cv2.hconcat(anteprime_step5)
    )

with open(OUTPUT / "step5_verifiche.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow([
        "fotografia", "zona", "dx_tavola", "dy_tavola",
        "dx_prima", "dy_prima", "qualita_prima",
        "dx_residuo", "dy_residuo", "qualita_dopo",
        "similarita_prima", "similarita_dopo"
    ])
    writer.writerows(righe_step5)

print("\nSTEP 5 completato: PNG e CSV salvati in", OUTPUT)