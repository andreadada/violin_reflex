"""STEP 4 | Verifica geometrica tramite punti caratteristici (OpenCV).

Scopo: controllare IN MODO INDIPENDENTE il residuo verticale di Riflesso_4,
confrontando punti riconoscibili (angoli, corde, bordi geometrici) anziche'
soltanto la correlazione di fase dei gradienti Sobel.

Questo script NON ALLINEA E NON MODIFICA alcun TIFF: legge tre immagini gia'
esistenti e crea SOLO report CSV/JSON e immagini diagnostiche PNG.

Requisiti: python -m pip install opencv-python numpy
Avvio:     python registration_step4.py

Percorsi richiesti, dalla cartella principale del progetto:
  images/Base.tif
  images/Riflesso_4.tif
  output/registered/Riflesso_4_registered.tif
  output/registration/step2_rotazione/04_trasformazioni.json

Come funziona, in breve:
  1) goodFeaturesToTrack: individua angoli e dettagli sulla Base.
  2) calcOpticalFlowPyrLK: cerca gli stessi dettagli nelle altre foto.
  3) Controllo avanti/indietro: elimina corrispondenze incerte.
  4) Normalized cross correlation delle piccole patch: verifica visiva locale.
  5) Mediana degli spostamenti su OGNI zona: misura robusta.

ATTENZIONE: le diverse luci possono falsare anche il tracking dei punti.
Questo e' un test indipendente di algoritmo, non una misura fisica perfetta.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "images" / "Base.tif"
ORIGINALE = ROOT / "images" / "Riflesso_4.tif"
REGISTRATO = ROOT / "output" / "registered" / "Riflesso_4_registered.tif"
TRASFORMAZIONI = ROOT / "output" / "registration" / "step2_rotazione" / "04_trasformazioni.json"
OUTPUT = ROOT / "output" / "registration" / "step4_punti"

# Coordinate RELATIVE al fotogramma: ciascuna misura usa un crop di 640 pixel
# NATIVI. Le foto vengono ridotte SOLO quando creiamo le panoramiche PNG.
LATO = 640
ZONE = {
    "tavola_sx": (0.32, 0.915),
    "tavola_dx": (0.69, 0.915),
    "alto_sx": (0.30, 0.17),
    "alto_dx": (0.70, 0.17),
    "corde": (0.50, 0.33),
    "effe_sx": (0.35, 0.43),
    "effe_dx": (0.65, 0.43),
    "basso_sx": (0.32, 0.70),
    "basso_dx": (0.68, 0.70),
}

# Parametri ragionevoli per un primo esperimento (NON soglie universali).
MAX_PUNTI = 110          # angoli iniziali cercati in ogni crop
MIN_PUNTI_ZONE = 8       # almeno 8 corrispondenze per considerare una zona
ERRORE_FB_MAX = 0.75     # errore round-trip Optical Flow, in pixel
CORR_PATCH_MIN = 0.35    # correlazione locale dopo CLAHE (da -1 a +1)
DISPERSIONE_MAX = 0.85   # mediana delle distanze fra spostamenti, in pixel
OUTLIER_MAX = 1.8       # massima distanza dalla mediana di gruppo, in pixel


def leggere_grigi(percorso: Path) -> np.ndarray:
    """Legge alla risoluzione ORIGINALE per la sola diagnostica geometrica.

    Il TIFF RGB rimane invariato sul disco; il grigio e' solo un'analisi.
    """
    img = cv2.imread(str(percorso), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"File mancante o non leggibile: {percorso}")
    return img


def leggi_fase(path: Path) -> tuple[float, float]:
    """dx e dy di Riflesso_4 RISPETTO alla Base (prima della registrazione)."""
    if not path.is_file():
        raise FileNotFoundError(f"Serve il JSON dello Step 2: {path}")
    d = json.loads(path.read_text(encoding="utf-8"))
    W = np.array(d["matrici_base_verso_riflesso"]["Phase"], dtype=np.float64)
    if W.shape != (2, 3) or not np.isfinite(W).all():
        raise ValueError("Matrice Phase assente/non valida")
    if not np.allclose(W[:, :2], np.eye(2), atol=1e-6):
        raise ValueError("La matrice non rappresenta una pura traslazione")
    return float(W[0, 2]), float(W[1, 2])


def box_crop(shape: tuple[int, int], pos: tuple[float, float], lato: int) -> tuple[int, int, int, int]:
    """Trova l'angolo del crop 640x640 nativo, controllando i margini."""
    h, w = shape
    x0 = round(pos[0] * w) - lato // 2
    y0 = round(pos[1] * h) - lato // 2
    if x0 < 0 or y0 < 0 or x0+lato > w or y0+lato > h:
        raise ValueError(f"Crop fuori dai limiti per posizione {pos}, forma {shape}")
    return x0, y0, x0+lato, y0+lato


def prepara_tracking(crop: np.ndarray) -> np.ndarray:
    """CLAHE migliora il contrasto locale per LK quando le luci cambiano.

    NON altera il TIFF: lavora su un piccolo ritaglio temporaneo.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    normale = clahe.apply(crop)
    return cv2.GaussianBlur(normale, (3, 3), 0.65)


def correlazione_patch(a: np.ndarray, b: np.ndarray, p: np.ndarray, q: np.ndarray,
                        lato: int = 17) -> float:
    """Quanto sono simili due piccole regioni attorno ai punti p e q?

    Sottraiamo la media locale: conta la struttura, meno la luminosita' media.
    Usa getRectSubPix per verificare anche coordinate frazionarie.
    """
    x, y = float(p[0]), float(p[1])
    xx, yy = float(q[0]), float(q[1])
    m = lato / 2 + 2
    if (min(x,y,xx,yy) < m or x > a.shape[1]-m or xx > b.shape[1]-m
            or y > a.shape[0]-m or yy > b.shape[0]-m):
        return float('nan')
    c = cv2.getRectSubPix(a, (lato, lato), (x, y)).astype(np.float32)
    d = cv2.getRectSubPix(b, (lato, lato), (xx, yy)).astype(np.float32)
    c -= c.mean(); d -= d.mean()
    den = float(np.linalg.norm(c)*np.linalg.norm(d))
    return float(np.sum(c*d) / den) if den > 1e-3 else float('nan')


def tracking_punti(base: np.ndarray, mobile: np.ndarray,
                   spostamento_iniziale: tuple[float,float],
                   feature_p0: np.ndarray | None = None) -> dict:
    """Cerca le corrispondenze con Lucas-Kanade piramidale.

    1) goodFeaturesToTrack fornisce p0=(x,y) in Base.
    2) OpenCV parte da p0+(dx,dy) e cerca il punto nella foto mobile.
    3) Ripete il tracking ALL'INDIETRO: mobile->Base.
    4) Tiene soltanto coppie coerenti e simili localmente.
    """
    a, b = prepara_tracking(base), prepara_tracking(mobile)
    if feature_p0 is None:
        # Evitiamo i margini del crop, fonte di tracking spurio.
        mask = np.zeros(a.shape, dtype=np.uint8)
        mask[35:-35, 35:-35] = 255
        p0 = cv2.goodFeaturesToTrack(a, maxCorners=MAX_PUNTI,
                                    qualityLevel=0.012, minDistance=12,
                                    mask=mask, blockSize=5)
        if p0 is None:
            p0 = np.empty((0, 1, 2), np.float32)
    else:
        p0 = np.asarray(feature_p0, np.float32).reshape(-1, 1, 2)

    if len(p0) == 0:
        return {"n_estratti":0, "p0":np.empty((0,2)), "p1":np.empty((0,2)),
                "displ":np.empty((0,2)), "scores":np.empty((0,))}

    p0 = cv2.cornerSubPix(a, p0.copy(), (5,5), (-1,-1),
                          (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 25, 0.01))
    # Un'immagine gia' registrata ha spostamento previsto (0,0).
    p1_init = p0.copy()
    p1_init[:,:,0] += spostamento_iniziale[0]
    p1_init[:,:,1] += spostamento_iniziale[1]
    params = dict(winSize=(25,25), maxLevel=3,
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.006))
    p1, ok_ab, _ = cv2.calcOpticalFlowPyrLK(a,b,p0,p1_init,
                                           flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **params)
    if p1 is None:
        return {"n_estratti":len(p0), "p0":np.empty((0,2)), "p1":np.empty((0,2)),
                "displ":np.empty((0,2)), "scores":np.empty((0,))}
    p0_ritorno, ok_ba, _ = cv2.calcOpticalFlowPyrLK(
        b,a,p1,p0.copy(),flags=cv2.OPTFLOW_USE_INITIAL_FLOW,**params)
    if p0_ritorno is None:
        return {"n_estratti":len(p0), "p0":np.empty((0,2)), "p1":np.empty((0,2)),
                "displ":np.empty((0,2)), "scores":np.empty((0,))}

    p0 = p0.reshape(-1,2); p1 = p1.reshape(-1,2)
    back = p0_ritorno.reshape(-1,2)
    fb = np.linalg.norm(p0-back, axis=1)
    valid = (ok_ab.ravel()>0) & (ok_ba.ravel()>0) & np.isfinite(fb) & (fb<=ERRORE_FB_MAX)
    scores = np.array([correlazione_patch(a,b,p,q) if good else float('nan')
                       for p,q,good in zip(p0,p1,valid)])
    valid &= np.isfinite(scores) & (scores>=CORR_PATCH_MIN)
    p0,p1,scores = p0[valid],p1[valid],scores[valid]
    return {"n_estratti":len(ok_ab), "p0":p0, "p1":p1,
            "displ":p1-p0,"scores":scores}


def filtra_misure(tracked: dict) -> dict:
    """Rimuove spostamenti isolati con mediana e produce statistiche per zona."""
    D = tracked['displ']
    if len(D) == 0:
        keep = np.zeros(0, bool)
        return {**tracked, "keep":keep, "dx":None,"dy":None,"dispersione":None,
                "n_buoni":0,"stato":"non conclusivo: nessun punto"}
    m = np.median(D,axis=0)
    distances = np.linalg.norm(D-m,axis=1)
    keep = distances<=OUTLIER_MAX
    sel = D[keep]
    if len(sel):
        mm = np.median(sel,axis=0)
        disp = float(np.median(np.linalg.norm(sel-mm,axis=1)))
        dx,dy = float(mm[0]),float(mm[1])
    else:
        disp=dx=dy=None
    good = len(sel)>=MIN_PUNTI_ZONE and disp is not None and disp<=DISPERSIONE_MAX
    return {**tracked,"keep":keep,"dx":dx,"dy":dy,
            "dispersione":disp,"n_buoni":int(keep.sum()),
            "stato":"affidabile per test" if good else "non conclusivo"}


def esamina(base: np.ndarray, orig: np.ndarray, registered: np.ndarray,
           phase: tuple[float,float], zone: dict=ZONE, lato: int=LATO) -> tuple[list, list, dict]:
    """Esegue il test a risoluzione nativa su tutte le zone specificate."""
    if not (base.shape==orig.shape==registered.shape):
        raise ValueError("Le tre fotografie hanno dimensioni differenti")
    if len(base.shape)!=2:
        raise ValueError("Le immagini per questa diagnostica devono essere in scala di grigi")
    rows, point_rows, per_region = [], [], {}
    for nome,center in zone.items():
        x0,y0,x1,y1 = box_crop(base.shape,center,lato)
        a=base[y0:y1,x0:x1]
        b=orig[y0:y1,x0:x1]
        c=registered[y0:y1,x0:x1]
        # Troviamo le stesse features su Base per entrambe le comparazioni.
        orig_points = tracking_punti(a,b,phase)
        post_points = tracking_punti(a,c,(0,0))
        per_region[nome] = {"bbox":(x0,y0,x1,y1),"originale":filtra_misure(orig_points),
                            "registrato":filtra_misure(post_points)}
        gruppo = "tavola" if nome.startswith('tavola') else "violino"
        for metodo in ('originale','registrato'):
            res=per_region[nome][metodo]
            rows.append({"zona":nome,"gruppo":gruppo,"metodo":metodo,
                         "punti_rilevati":res['n_estratti'],"punti_validi":res['n_buoni'],
                         "dx_median_px":res['dx'],"dy_median_px":res['dy'],
                         "dispersione_px":res['dispersione'],
                         "corr_patch_mediana":float(np.median(res['scores'][res['keep']])) if res['n_buoni'] else None,
                         "stato":res['stato']})
            for i, (p,q,disp,keep,sc) in enumerate(zip(res['p0'],res['p1'],res['displ'],res['keep'],res['scores'])):
                point_rows.append({"zona":nome,"gruppo":gruppo,"metodo":metodo,
                                   "id":i,"x_base":round(float(x0+p[0]),4),
                                   "y_base":round(float(y0+p[1]),4),
                                   "x_mobile":round(float(x0+q[0]),4),
                                   "y_mobile":round(float(y0+q[1]),4),
                                   "dx":round(float(disp[0]),4),"dy":round(float(disp[1]),4),
                                   "corr_patch":round(float(sc),4),"inlier":int(keep)})
        print(f"{nome:11s}  punti LK prima={per_region[nome]['originale']['n_buoni']:3d} "
              f"dopo={per_region[nome]['registrato']['n_buoni']:3d}  "
              f"residuo dopo=({per_region[nome]['registrato']['dx']}, {per_region[nome]['registrato']['dy']})  "
              f"{per_region[nome]['registrato']['stato']}")
    return rows,point_rows,per_region


def aggrega(rows: list) -> dict:
    """Aggrega per zona, non per numero totale di corner (evita dominio tavola)."""
    summary={}
    for gruppo in ('tavola','violino'):
        for metodo in ('originale','registrato'):
            valid=[r for r in rows if r['gruppo']==gruppo and r['metodo']==metodo
                   and r['stato']=='affidabile per test']
            val=np.array([[r['dx_median_px'],r['dy_median_px']] for r in valid],np.float64)
            summary[f"{gruppo}_{metodo}"]={"zone_affidabili":len(valid),"zone": [r['zona'] for r in valid],
                "dx_median_px":float(np.median(val[:,0])) if len(val) else None,
                "dy_median_px":float(np.median(val[:,1])) if len(val) else None}
    a=summary['tavola_registrato']; b=summary['violino_registrato']
    if a['zone_affidabili']>=2 and b['zone_affidabili']>=3:
        diff=b['dy_median_px']-a['dy_median_px']
        state=("differenza verticale da approfondire; non correggere automaticamente" if abs(diff)>=0.5
               else "differenza verticale contenuta entro 0.5 px secondo LK")
    else:
        diff=None
        state="NON CONCLUSIVO: servono almeno 2 zone tavola e 3 zone violino affidabili"
    summary['confronto_verticale']={"delta_violino_meno_tavola_px":diff,"esito":state}
    return summary


def write_csv(path:Path,rows:list) -> None:
    if not rows: return
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def resize_preview(im:np.ndarray,max_height=1200) -> tuple[np.ndarray,float]:
    h,w=im.shape[:2]
    s=min(1.0,max_height/h)
    if s==1: return im.copy(),s
    return cv2.resize(im,(round(w*s),round(h*s)),interpolation=cv2.INTER_AREA),s


def mappa_zone(base:np.ndarray, per_region:dict) -> np.ndarray:
    """Mostra su Base tutte le aree e i punti tracciati attendibili."""
    vis,scale=resize_preview(cv2.cvtColor(base,cv2.COLOR_GRAY2BGR), 1350)
    for nome, data in per_region.items():
        x0,y0,x1,y1=data['bbox']; r=data['registrato']
        green=r['stato']=='affidabile per test'; color=(65,210,80) if green else (0,180,255)
        p0=(round(x0*scale),round(y0*scale));p1=(round(x1*scale),round(y1*scale))
        cv2.rectangle(vis,p0,p1,color,2)
        value=(f"{r['dx']:+.2f},{r['dy']:+.2f}" if r['dx'] is not None else "N/D")
        label=f"{nome}: {value} | n={r['n_buoni']}"
        cv2.putText(vis,label,(p0[0],max(17,p0[1]-8)),cv2.FONT_HERSHEY_SIMPLEX,
                    .48,color,1,cv2.LINE_AA)
        # Mostriamo i punti matched registrati; coord. assolute in Base.
        for p,good in zip(r['p0'],r['keep']):
            if not good:continue
            cx=round((x0+p[0])*scale);cy=round((y0+p[1])*scale)
            cv2.circle(vis,(cx,cy),2,(0,245,255),-1,cv2.LINE_AA)
    banner=np.full((95,vis.shape[1],3),27,np.uint8)
    cv2.putText(banner,"REGISTRAZIONE: TRACKING DEI PUNTI (LUCAS-KANADE)",(14,28),
                cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),1,cv2.LINE_AA)
    cv2.putText(banner,"Verde = zona affidabile; arancione = verifica non conclusiva",(14,56),
                cv2.FONT_HERSHEY_SIMPLEX,.47,(240,240,240),1,cv2.LINE_AA)
    cv2.putText(banner,"Punti gialli = corrispondenze conservate; etichette dx,dy in pixel nativi",(14,78),
                cv2.FONT_HERSHEY_SIMPLEX,.42,(240,240,240),1,cv2.LINE_AA)
    return cv2.vconcat((banner,vis))


def confronto_crops(base:np.ndarray, orig:np.ndarray, reg:np.ndarray, per_region:dict) -> np.ndarray:
    """Griglia grande prima/dopo, da foto originali in grigio + markers.

    Overlay: Rosso=Base, Ciano=Riflesso_4; punti gialli trovati da LK.
    """
    panels=[]
    for nome,record in per_region.items():
        x0,y0,x1,y1=record['bbox']
        a=base[y0:y1,x0:x1]
        for key,mob in [('originale',orig),('registrato',reg)]:
            b=mob[y0:y1,x0:x1]
            overlay=cv2.merge([b,b,a])
            track=record[key]
            # Interponiamo un'immagine senza pittura sul bordo del crop, per non
            # nascondere punti diagnostici con i titoli.
            for p,good in zip(track['p0'],track['keep']):
                if not good: continue
                cv2.circle(overlay,(round(float(p[0])),round(float(p[1]))),3,
                           (0,245,255),-1,cv2.LINE_AA)
            h,w=overlay.shape[:2]
            board=np.full((h+44,w,3),22,np.uint8)
            board[44:]=overlay
            dx=track['dx'];dy=track['dy']
            msg=f"{nome} {key.upper()} | n={track['n_buoni']} "
            if dx is not None:msg+=f"dx={dx:+.2f} dy={dy:+.2f}"
            cv2.putText(board,msg,(8,29),cv2.FONT_HERSHEY_SIMPLEX,.52,(255,255,255),1,cv2.LINE_AA)
            panels.append(board)
    # 2 colonne: originale e registrato, una riga per regione.
    w=next(iter(per_region.values()))['bbox'][2]-next(iter(per_region.values()))['bbox'][0]
    h=w+44
    arr=cv2.vconcat([cv2.hconcat(panels[i:i+2]) for i in range(0,len(panels),2)])
    header=np.full((68,arr.shape[1],3),25,np.uint8)
    cv2.putText(header,"ROSSO = BASE   |   CIANO = RIFLESSO 4   |   GIALLO = PUNTI SEGUITI",(15,28),
                cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1,cv2.LINE_AA)
    cv2.putText(header,"PRIMA (sinistra) vs REGISTRATO (destra) - crop originali, nessun resize",(15,53),
                cv2.FONT_HERSHEY_SIMPLEX,.49,(210,210,210),1,cv2.LINE_AA)
    return cv2.vconcat((header,arr))


def mappa_vettori(base:np.ndarray, per_region:dict) -> np.ndarray:
    """Vettori di disallineamento volutamente amplificati SOLO per vederli.

    Scala grafica x35: la lunghezza della freccia NON e' un pixel reale.
    """
    img,sc=resize_preview(cv2.cvtColor(base,cv2.COLOR_GRAY2BGR),1000)
    h,w=img.shape[:2]
    pane=[]
    for key,title in [('originale','PRIMA'),('registrato','DOPO')]:
        part=img.copy()
        for name,region in per_region.items():
            x0,y0,x1,y1=region['bbox']; d=region[key]
            if d['stato']!='affidabile per test':continue
            x=round(((x0+x1)/2)*sc);y=round(((y0+y1)/2)*sc)
            tx=round(x+d['dx']*35);ty=round(y+d['dy']*35)
            col=(0,230,245) if name.startswith('tavola') else (80,245,90)
            cv2.circle(part,(x,y),5,col,-1)
            cv2.arrowedLine(part,(x,y),(tx,ty),col,2,tipLength=.20)
        title_line=np.full((70,w,3),25,np.uint8)
        cv2.putText(title_line,title+' - VETTORI x35 (SOLO VISUALIZZAZIONE)',(12,26),
                    cv2.FONT_HERSHEY_SIMPLEX,.49,(255,255,255),1)
        cv2.putText(title_line,'Giallo = tavola, verde = violino (frecce ingrandite)',(12,55),
                    cv2.FONT_HERSHEY_SIMPLEX,.40,(200,200,200),1)
        pane.append(cv2.vconcat((title_line,part)))
    return cv2.hconcat(pane)


def run(base_path:Path=BASE, orig_path:Path=ORIGINALE, reg_path:Path=REGISTRATO,
        trans_path:Path=TRASFORMAZIONI, output:Path=OUTPUT,
        zone:dict=ZONE, lato:int=LATO) -> dict:
    """Coordina la verifica, e salva SOLO PNG + CSV + JSON."""
    print("STEP 4 - PUNTI GEOMETRICI / Lucas-Kanade")
    phase=leggi_fase(trans_path)
    print(f"Stima iniziale Phase prima della correzione: dx={phase[0]:+.3f} dy={phase[1]:+.3f}")
    base,orig,reg=[leggere_grigi(p) for p in (base_path,orig_path,reg_path)]
    if not (base.shape==orig.shape==reg.shape):
        raise ValueError("Le tre fotografie non hanno esattamente la stessa risoluzione")
    print(f"Tre immagini: {base.shape[1]}x{base.shape[0]} pixel nativi, nessuna scrittura TIFF")
    rows,point_rows,parts=esamina(base,orig,reg,phase,zone=zone,lato=lato)
    report={"metodo":"goodFeaturesToTrack + PyrLK forward/backward + correlazione patch + mediane per regione",
            "phase_dxdy_originale":list(phase),"risoluzione_native":list(base.shape[::-1]),
            "parametri":{"crop_lato":lato,"errore_round_trip_max":ERRORE_FB_MAX,
                         "correlazione_patch_min":CORR_PATCH_MIN,"punti_min_per_zona":MIN_PUNTI_ZONE,
                         "dispersione_max_px":DISPERSIONE_MAX},
            "sintesi":aggrega(rows),"originali_modificati":False,
            "avvertenza":"La fotometria cambia tra gli scatti; anche LK puo' essere falsato. Niente correzione aggiuntiva automatica."}
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output/'04_misure_zone.csv',rows)
    write_csv(output/'05_punti_correlati.csv',point_rows)
    for filename,im in [('01_mappa_zone.png',mappa_zone(base,parts)),
                        ('02_confronto_punti.png',confronto_crops(base,orig,reg,parts)),
                        ('03_vettori_prima_dopo.png',mappa_vettori(base,parts))]:
        if not cv2.imwrite(str(output/filename),im):
            raise OSError(f"Impossibile salvare {filename}")
    (output/'06_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print("\nESITO:",report['sintesi']['confronto_verticale']['esito'])
    print("Risultati salvati in:", output)
    return report


if __name__=='__main__':
    run()