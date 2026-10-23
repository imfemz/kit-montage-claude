#!/usr/bin/env python3
"""Dérush « blancs seulement » : raccourcit les silences, ne retire aucun mot.

Règles :
  - chaque blanc entre deux mots qui dure au moins --blanc-min secondes est raccourci
    pour n'en garder qu'environ --garder secondes (le début et la fin d'un blanc
    sont aussi raccourcis : avant le premier mot, après le dernier) ;
  - les deux points de coupe tombent au creux d'énergie de la voix dans le blanc
    (RMS par fenêtres de 10 ms sur l'audio mono 16 kHz) ;
  - aucun point de coupe à moins de --marge secondes (40 ms par défaut) d'un mot ;
  - si la source est une vidéo, les coupes sont posées sur des limites d'image,
    pour que l'image et le son restent synchrones après le montage.

Garde-fou : si la partie à retirer contient du son (au moins 150 ms à moins de 12 dB
sous le niveau de la voix : mot non transcrit, musique, rire), le blanc n'est PAS
raccourci ; il est listé dans « blancs_sonores_non_coupes » pour être écouté
(--couper-blancs-sonores force la coupe).

Les « reprises possibles » (une même suite d'au moins 3 mots répétée à moins de
10 s d'écart) sont listées pour validation humaine, jamais coupées.

Sortie (cutlist.json) : {"segments": [{"debut": s, "fin": s}, ...], "blancs_raccourcis": [...],
"reprises_possibles": [...], "duree_source": s, "duree_apres": s, ...}
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (ErreurKit, decoder_audio, ecrire_json, executer, exiger_fichier, fmt_duree,
                    lire_json, sonder, verifier_outils)

PAS = 0.010             # fenêtres d'énergie de 10 ms
SR = 16000
PLANCHER_DB = -120.0
PENALITE_DB = 6.0       # coût (en dB d'énergie cumulée) d'un écart de 100 % à la durée gardée visée
TOLERANCE_GARDE = (0.7, 1.5)   # la durée gardée peut varier entre 70 % et 150 % de --garder
SOUS_LA_VOIX_DB = 12.0  # au-dessus de (voix − 12 dB), un passage sans mot contient du son
SON_MIN = 0.15          # une plage sonore de 150 ms dans la partie à retirer bloque la coupe


# --------------------------------------------------------------------------- énergie

def rms_par_fenetre(audio: np.ndarray, sr: int = SR, pas: float = PAS) -> np.ndarray:
    """RMS de l'audio par fenêtres consécutives de `pas` secondes, en dBFS."""
    n = max(1, int(round(sr * pas)))
    nb = len(audio) // n
    if nb == 0:
        return np.full(1, PLANCHER_DB)
    x = audio[: nb * n].astype(np.float64).reshape(nb, n)
    rms = np.sqrt(np.mean(x * x, axis=1))
    return np.maximum(20 * np.log10(np.maximum(rms, 1e-12)), PLANCHER_DB)


def energie_aux(temps: np.ndarray, db: np.ndarray, pas: float = PAS) -> np.ndarray:
    """Énergie (dB) autour de chaque instant : moyenne des deux fenêtres de 10 ms qui l'encadrent."""
    i = np.rint(np.asarray(temps) / pas).astype(int)
    g = np.clip(i - 1, 0, len(db) - 1)
    d = np.clip(i, 0, len(db) - 1)
    lin = (10 ** (db[g] / 10) + 10 ** (db[d] / 10)) / 2
    return 10 * np.log10(np.maximum(lin, 1e-12))


# --------------------------------------------------------------------------- grille de coupe

class Grille:
    """Instants où une coupe est permise : limites d'image (vidéo) ou pas de 10 ms (audio seul)."""

    def __init__(self, fps: Fraction | None = None, decalage: float = 0.0):
        self.fps = fps
        self.decalage = decalage if fps else 0.0
        self.pas = float(1 / fps) if fps else PAS

    def entre(self, lo: float, hi: float) -> np.ndarray:
        if hi < lo:
            return np.empty(0)
        k0 = math.ceil((lo - self.decalage) / self.pas - 1e-9)
        k1 = math.floor((hi - self.decalage) / self.pas + 1e-9)
        if k1 < k0:
            return np.empty(0)
        return self.decalage + np.arange(k0, k1 + 1) * self.pas


# --------------------------------------------------------------------------- mots et blancs

def mots_tries(mots: list[dict]) -> list[dict]:
    propres = []
    for m in mots:
        try:
            d, f = float(m["debut"]), float(m["fin"])
        except (KeyError, TypeError, ValueError) as e:
            raise ErreurKit(f"mot mal formé dans le transcript : {m!r}") from e
        propres.append({**m, "debut": d, "fin": max(d, f)})
    return sorted(propres, key=lambda m: (m["debut"], m["fin"]))


def blancs(mots: list[dict], duree: float) -> list[tuple[float, float, str]]:
    """Intervalles sans mot : (debut, fin, sorte) avec sorte = debut | milieu | fin."""
    if not mots:
        return [(0.0, duree, "vide")]
    out = [(0.0, mots[0]["debut"], "debut")]
    fin_max = mots[0]["fin"]
    for m in mots[1:]:
        if m["debut"] > fin_max:
            out.append((fin_max, m["debut"], "milieu"))
        fin_max = max(fin_max, m["fin"])
    out.append((fin_max, duree, "fin"))
    return out


def planifier_blanc(a: float, b: float, sorte: str, db: np.ndarray, grille: Grille,
                    garder: float, marge: float):
    """Choisit l'intervalle à retirer dans le blanc [a, b]. Renvoie (c1, c2) ou None."""
    kmin = max(garder * TOLERANCE_GARDE[0], marge * (2 if sorte == "milieu" else 1))
    kmax = max(kmin, garder * TOLERANCE_GARDE[1])
    min_retire = 2 * grille.pas

    def penalite(garde):
        return PENALITE_DB * np.abs(garde - garder) / max(garder, 1e-6)

    if sorte == "milieu":
        A = grille.entre(a + marge, min(a + kmax - marge, b - marge))
        B = grille.entre(max(b - kmax + marge, a + marge), b - marge)
        if len(A) == 0 or len(B) == 0:
            return None
        eA, eB = energie_aux(A, db), energie_aux(B, db)
        garde = (A[:, None] - a) + (b - B[None, :])
        ok = (garde >= kmin - 1e-9) & (garde <= kmax + 1e-9) & (B[None, :] - A[:, None] >= min_retire)
        if not ok.any():
            return None
        score = np.where(ok, eA[:, None] + eB[None, :] + penalite(garde), np.inf)
        i, j = np.unravel_index(np.argmin(score), score.shape)
        return float(A[i]), float(B[j])

    if sorte == "debut":            # avant le premier mot : on retire [0, c2]
        B = grille.entre(b - kmax, b - kmin)
        B = B[B >= min_retire]
        if len(B) == 0:
            return None
        score = energie_aux(B, db) + penalite(b - B)
        return 0.0, float(B[np.argmin(score)])

    if sorte == "fin":              # après le dernier mot : on retire [c1, fin]
        A = grille.entre(a + kmin, a + kmax)
        A = A[A <= b - min_retire]
        if len(A) == 0:
            return None
        score = energie_aux(A, db) + penalite(A - a)
        return float(A[np.argmin(score)]), b
    return None


def seuil_sonore(db: np.ndarray, mots: list[dict], pas: float = PAS) -> float:
    """Niveau au-dessus duquel un passage « sans mot » contient en fait du son (mot non transcrit,
    musique, rire…) : 12 dB sous le niveau médian de la voix, et au moins 6 dB au-dessus du bruit
    de fond. Une respiration (en général 15 à 30 dB sous la voix) reste en dessous."""
    dans_mots = np.zeros(len(db), dtype=bool)
    for m in mots:
        dans_mots[int(m["debut"] / pas):int(math.ceil(m["fin"] / pas))] = True
    voix = float(np.median(db[dans_mots])) if dans_mots.any() else float(np.median(db))
    hors = db[~dans_mots] if (~dans_mots).any() else db
    plancher = float(np.percentile(hors, 10))
    return max(voix - SOUS_LA_VOIX_DB, plancher + 6.0)


def son_dans(db: np.ndarray, c1: float, c2: float, seuil: float, pas: float = PAS) -> float:
    """Durée (s) de la plus longue plage au-dessus de `seuil` dans [c1, c2], énergie lissée sur 50 ms."""
    i0, i1 = max(0, int(c1 / pas)), min(len(db), int(math.ceil(c2 / pas)))
    if i1 <= i0:
        return 0.0
    lin = 10 ** (db[i0:i1] / 10)
    lisse = np.convolve(lin, np.ones(5) / 5, mode="same")
    fort = 10 * np.log10(np.maximum(lisse, 1e-12)) > seuil
    plus_long = courant = 0
    for v in fort:
        courant = courant + 1 if v else 0
        plus_long = max(plus_long, courant)
    return plus_long * pas


def planifier(mots: list[dict], duree: float, db: np.ndarray, grille: Grille,
              blanc_min: float = 1.0, garder: float = 0.25, marge: float = 0.040,
              couper_blancs_sonores: bool = False):
    """Calcule les segments à garder, les blancs raccourcis et les blancs laissés intacts parce
    qu'ils contiennent du son (à vérifier à l'oreille)."""
    mots = mots_tries(mots)
    seuil = seuil_sonore(db, mots)
    retraits, raccourcis, sonores = [], [], []
    for a, b, sorte in blancs(mots, duree):
        if sorte == "vide" or b - a < blanc_min:
            continue
        choix = planifier_blanc(a, b, sorte, db, grille, garder, marge)
        if choix is None:
            continue
        c1, c2 = choix
        son = son_dans(db, c1, c2, seuil)
        if son >= SON_MIN and not couper_blancs_sonores:
            sonores.append({"sorte": sorte, "debut": round(a, 3), "fin": round(b, 3), "duree": round(b - a, 3),
                            "son_continu": round(son, 2), "seuil_db": round(seuil, 1)})
            continue
        garde = (c1 - a) + (b - c2)
        raccourcis.append({
            "sorte": sorte, "debut": round(a, 3), "fin": round(b, 3), "duree": round(b - a, 3),
            "coupe": [round(c1, 6), round(c2, 6)], "garde": round(garde, 3),
            "energie_db": [round(float(energie_aux([c], db)[0]), 1) for c in (c1, c2) if 0 < c < duree],
        })
        retraits.append((c1, c2))

    segments, curseur = [], 0.0
    for c1, c2 in retraits:
        if c1 > curseur:
            segments.append({"debut": round(curseur, 6), "fin": round(c1, 6)})
        curseur = max(curseur, c2)
    if curseur < duree:
        segments.append({"debut": round(curseur, 6), "fin": round(duree, 6)})
    return segments, raccourcis, sonores


def verifier_coupes(segments: list[dict], mots: list[dict], marge: float,
                    duree: float | None = None) -> list[str]:
    """Contrôle de sûreté : aucun mot coupé, aucun point de coupe à moins de `marge` d'un mot."""
    problemes = []
    mots = mots_tries(mots)
    for m in mots:
        if not any(s["debut"] - 1e-6 <= m["debut"] and m["fin"] <= s["fin"] + 1e-6 for s in segments):
            problemes.append(f"mot retiré ou coupé : « {m.get('mot', '?')} » ({m['debut']:.2f} s)")
    bornes = {s["debut"] for s in segments} | {s["fin"] for s in segments}
    coupes = [c for c in bornes if c > 1e-6 and (duree is None or c < duree - 1e-6)]
    for c in coupes:
        for m in mots:
            if m["debut"] - marge + 1e-6 < c < m["fin"] + marge - 1e-6:
                problemes.append(f"coupe à {c:.3f} s trop près de « {m.get('mot', '?')} » "
                                 f"({m['debut']:.3f}-{m['fin']:.3f} s)")
    return problemes


# --------------------------------------------------------------------------- reprises

def _normaliser(mot: str) -> str:
    mot = mot.lower().replace("’", "'")
    return re.sub(r"[^\w']+", "", mot).strip("'")


def reprises_possibles(mots: list[dict], n_min: int = 3, ecart_max: float = 10.0) -> list[dict]:
    """Suites d'au moins `n_min` mots identiques répétées à moins de `ecart_max` s (début à début)."""
    mots = mots_tries(mots)
    toks = [_normaliser(m["mot"]) for m in mots]
    n = len(mots)
    trouvees = []
    for i in range(n):
        if not toks[i]:
            continue
        for j in range(i + 1, n):
            if mots[j]["debut"] - mots[i]["debut"] > ecart_max:
                break
            if toks[j] != toks[i]:
                continue
            if i > 0 and toks[i - 1] and toks[i - 1] == toks[j - 1] and j - 1 > i:
                continue        # déjà comptée dans une suite plus longue qui commence avant
            k = 0
            while j + k < n and i + k < j and toks[i + k] and toks[i + k] == toks[j + k]:
                k += 1
            if k >= n_min:
                texte = lambda a, b: " ".join(m["mot"] for m in mots[a:b])
                trouvees.append({
                    "texte": texte(i, i + k),
                    "mots": k,
                    "premiere": {"debut": round(mots[i]["debut"], 3), "fin": round(mots[i + k - 1]["fin"], 3)},
                    "seconde": {"debut": round(mots[j]["debut"], 3), "fin": round(mots[j + k - 1]["fin"], 3)},
                    "entre_les_deux": texte(i, j)[:200],
                    "si_valide_couper": {"debut": round(mots[i]["debut"], 3), "fin": round(mots[j]["debut"], 3)},
                })
    return trouvees


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Raccourcit les blancs (aucun mot retiré) et liste les reprises possibles → cutlist.json.",
        epilog="Exemple : python scripts/derush.py rush.mp4 transcript.json --blanc-min 1.0 --garder 0.25",
    )
    ap.add_argument("video", help="vidéo (ou audio) d'origine")
    ap.add_argument("transcript", help="transcript.json écrit par transcrire.py")
    ap.add_argument("--blanc-min", type=float, default=1.0, help="durée minimale d'un blanc à raccourcir, en s (défaut : 1.0)")
    ap.add_argument("--garder", type=float, default=0.25, help="silence à garder par blanc, en s (défaut : 0.25)")
    ap.add_argument("--marge", type=float, default=0.040, help="distance minimale entre une coupe et un mot, en s (défaut : 0.040)")
    ap.add_argument("--reprise-mots", type=int, default=3, help="longueur minimale d'une reprise, en mots (défaut : 3)")
    ap.add_argument("--reprise-ecart", type=float, default=10.0, help="écart maximal entre deux prises, en s (défaut : 10)")
    ap.add_argument("--couper-blancs-sonores", action="store_true",
                    help="raccourcit aussi les blancs où l'on entend du son sans mot transcrit (désactivé par défaut)")
    ap.add_argument("--sortie", help="fichier de sortie (défaut : cutlist.json à côté de la vidéo)")
    a = ap.parse_args(argv)

    if a.marge < 0.040:
        raise ErreurKit("--marge doit valoir au moins 0.040 s")
    if a.garder < 2 * a.marge:
        raise ErreurKit(f"--garder doit valoir au moins 2 × marge = {2 * a.marge:.3f} s")
    if a.blanc_min <= a.garder * TOLERANCE_GARDE[1]:
        raise ErreurKit(f"--blanc-min doit dépasser {a.garder * TOLERANCE_GARDE[1]:.2f} s (1,5 × --garder)")

    verifier_outils("ffmpeg", "ffprobe")
    video = exiger_fichier(a.video)
    tr = lire_json(a.transcript)
    if "mots" not in tr:
        raise ErreurKit("le transcript ne contient pas de liste « mots » (utilise transcrire.py)")
    mots = tr["mots"]

    info = sonder(video)
    if not info["a_audio"]:
        raise ErreurKit(f"{video.name} n'a pas de piste audio")
    duree = info["duree"]
    print("analyse de l'énergie de la voix…", file=sys.stderr)
    db = rms_par_fenetre(decoder_audio(video, SR))
    grille = Grille(info["fps"], info["decalage_video"])

    segments, raccourcis, sonores = planifier(mots, duree, db, grille, a.blanc_min, a.garder, a.marge,
                                              a.couper_blancs_sonores)
    problemes = verifier_coupes(segments, mots, a.marge, duree)
    if problemes:
        raise ErreurKit("contrôle des coupes en échec (bug à signaler) :\n  " + "\n  ".join(problemes[:10]))
    reprises = reprises_possibles(mots, a.reprise_mots, a.reprise_ecart)

    duree_apres = sum(s["fin"] - s["debut"] for s in segments)
    sortie = Path(a.sortie) if a.sortie else video.parent / "cutlist.json"
    ecrire_json(sortie, {
        "source": video.name,
        "duree_source": round(duree, 3),
        "duree_apres": round(duree_apres, 3),
        "fps": str(info["fps"]) if info["fps"] else None,
        "parametres": {"blanc_min": a.blanc_min, "garder": a.garder, "marge": a.marge},
        "segments": segments,
        "blancs_raccourcis": raccourcis,
        "blancs_sonores_non_coupes": sonores,
        "reprises_possibles": reprises,
    })

    print(f"blancs raccourcis : {len(raccourcis)} (≥ {a.blanc_min:g} s) — aucun mot retiré")
    print(f"durée : {fmt_duree(duree)} → {fmt_duree(duree_apres)} "
          f"(−{fmt_duree(duree - duree_apres)}, {len(segments)} segments, {max(0, len(segments) - 1)} raccords)")
    if sonores:
        print(f"blancs NON coupés car on y entend du son (mot non transcrit, musique ?) : {len(sonores)} — à écouter")
        for b in sonores[:10]:
            print(f"  {b['debut']:7.2f} → {b['fin']:7.2f} s ({b['duree']:.1f} s)")
    if reprises:
        print(f"reprises possibles à valider : {len(reprises)} (non coupées)")
        for r in reprises[:10]:
            print(f"  {r['premiere']['debut']:7.2f} s et {r['seconde']['debut']:7.2f} s : « {r['texte']} »")
        if len(reprises) > 10:
            print(f"  … et {len(reprises) - 10} autres dans le fichier")
    else:
        print("reprises possibles : aucune")
    print(f"→ {sortie}")
    return 0


if __name__ == "__main__":
    executer(main)
