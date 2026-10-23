#!/usr/bin/env python3
"""Mesure EBU R128 d'un fichier audio ou vidéo (filtre ebur128 de ffmpeg).

Affiche la sonie intégrée (LUFS), le true peak (dBTP), la plage de sonie (LRA) et la
sonie de chaque fenêtre de 10 s. Une fenêtre qui s'écarte de plus de ±4 LU de la médiane
des fenêtres est signalée comme « variation ». Cible affichée : −14 LUFS, true peak ≤ −1 dBTP.

La sonie d'une fenêtre est calculée comme la sonie intégrée (BS.1770 : blocs de 400 ms,
porte absolue −70 LUFS, porte relative −10 LU) sur les seuls blocs contenus dans la fenêtre.
"""

from __future__ import annotations

import argparse
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ErreurKit, ecrire_json, executer, exiger_fichier, lancer, sonder, verifier_outils

CIBLE_LUFS = -14.0
CIBLE_TP = -1.0
FENETRE = 10.0
ECART_VARIATION = 4.0
BLOC = 0.4
PART_SONORE_MIN = 0.1       # sous 10 % de blocs au-dessus de −70 LUFS, la fenêtre est un silence

_RE_BLOC = re.compile(r"t:\s*([0-9.]+)\s+TARGET:.*?M:\s*(-?inf|nan|-?[0-9.]+)")
_RE_I = re.compile(r"Integrated loudness:\s*I:\s*(-?inf|-?[0-9.]+)\s*LUFS", re.S)
_RE_LRA = re.compile(r"Loudness range:\s*LRA:\s*(-?[0-9.]+)\s*LU", re.S)
_RE_TP = re.compile(r"True peak:\s*Peak:\s*(-?inf|-?[0-9.]+)\s*dBFS", re.S)


def _f(x: str) -> float:
    return float("-inf") if "inf" in x or x == "nan" else float(x)


def sonie_integree(momentanees: list[float]) -> float:
    """Sonie intégrée (BS.1770) à partir de sonies de blocs de 400 ms (LUFS)."""
    blocs = [m for m in momentanees if m > -70.0]
    if not blocs:
        return float("-inf")
    energie = lambda xs: sum(10 ** ((x + 0.691) / 10) for x in xs) / len(xs)
    seuil = -0.691 + 10 * math.log10(energie(blocs)) - 10.0
    gardes = [m for m in blocs if m > seuil]
    return -0.691 + 10 * math.log10(energie(gardes))


def mesurer(chemin: str | Path, fenetre: float = FENETRE) -> dict:
    """Mesure EBU R128 complète + sonie par fenêtres. Lève ErreurKit si pas de son."""
    verifier_outils("ffmpeg", "ffprobe")
    chemin = exiger_fichier(chemin)
    if not sonder(chemin)["a_audio"]:
        raise ErreurKit(f"{chemin.name} n'a pas de piste audio")
    proc = lancer(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-vn", "-sn", "-dn", "-i", str(chemin),
                   "-filter_complex", "[0:a:0]ebur128=peak=true:framelog=info", "-f", "null", "-"])
    err = proc.stderr
    resume = err[err.rfind("Summary:"):]
    mi, ml, mt = _RE_I.search(resume), _RE_LRA.search(resume), _RE_TP.search(resume)
    if not (mi and ml and mt):
        raise ErreurKit("impossible de lire le résumé du filtre ebur128 (version de ffmpeg ?)")

    blocs = [(float(t), _f(m)) for t, m in _RE_BLOC.findall(err)]
    duree = blocs[-1][0] if blocs else 0.0
    fenetres = []
    k = 0
    while k * fenetre < duree - 1e-6:
        a, b = k * fenetre, min(duree, (k + 1) * fenetre)
        # bloc de 400 ms qui finit à t : entièrement dans la fenêtre si a <= t-0.4 et t <= b
        dedans = [m for t, m in blocs if t - BLOC >= a - 0.01 and t <= b + 0.01]
        if b - a >= 1.0:
            sonores = sum(1 for m in dedans if m > -70.0)
            fenetres.append({"debut": round(a, 1), "fin": round(b, 1), "lufs": sonie_integree(dedans),
                             "part_sonore": sonores / max(1, len(dedans))})
        k += 1
    sonores = [f["lufs"] for f in fenetres if f["part_sonore"] >= PART_SONORE_MIN]
    mediane = statistics.median(sonores) if sonores else None
    for f in fenetres:
        if f.pop("part_sonore") < PART_SONORE_MIN:
            f["etat"] = "silence"
        elif mediane is not None and abs(f["lufs"] - mediane) > ECART_VARIATION:
            f["etat"] = "variation"
        else:
            f["etat"] = "ok"
        f["lufs"] = round(f["lufs"], 1) if math.isfinite(f["lufs"]) else None

    integree = _f(mi.group(1))
    return {
        "fichier": chemin.name,
        "integree_lufs": round(integree, 1) if math.isfinite(integree) else None,
        "true_peak_dbtp": round(_f(mt.group(1)), 1) if math.isfinite(_f(mt.group(1))) else None,
        "lra_lu": round(float(ml.group(1)), 1),
        "fenetre_s": fenetre,
        "mediane_fenetres_lufs": round(mediane, 1) if mediane is not None else None,
        "fenetres": fenetres,
        "variations": [f for f in fenetres if f["etat"] != "ok"],
        "cible": {"lufs": CIBLE_LUFS, "true_peak_dbtp": CIBLE_TP},
    }


def rapport(m: dict) -> str:
    i, tp = m["integree_lufs"], m["true_peak_dbtp"]
    ecart = f"{i - CIBLE_LUFS:+.1f} LU" if i is not None else "—"
    ok_i = i is not None and abs(i - CIBLE_LUFS) <= 0.5
    ok_tp = tp is not None and tp <= CIBLE_TP
    L = [f"NIVEAU — {m['fichier']}",
         f"  sonie intégrée : {i if i is not None else '—'} LUFS   (cible {CIBLE_LUFS:g}, écart {ecart}) "
         f"{'OK' if ok_i else 'hors cible'}",
         f"  true peak      : {tp if tp is not None else '—'} dBTP   (cible ≤ {CIBLE_TP:g}) {'OK' if ok_tp else 'trop haut'}",
         f"  LRA            : {m['lra_lu']} LU",
         f"  fenêtres de {m['fenetre_s']:g} s : {len(m['fenetres'])}, médiane "
         f"{m['mediane_fenetres_lufs'] if m['mediane_fenetres_lufs'] is not None else '—'} LUFS"]
    if m["variations"]:
        L.append(f"  variations (> ±{ECART_VARIATION:g} LU de la médiane) : {len(m['variations'])}")
        for f in m["variations"]:
            val = f"{f['lufs']} LUFS" if f["lufs"] is not None else "silence"
            L.append(f"    {f['debut']:7.1f} → {f['fin']:7.1f} s : {val}")
    else:
        L.append("  variations : aucune")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Mesure EBU R128 : sonie intégrée, true peak, LRA et variations par fenêtres de 10 s.",
        epilog="Exemple : python scripts/niveau.py exports/final.mp4",
    )
    ap.add_argument("fichier", help="fichier audio ou vidéo à mesurer")
    ap.add_argument("--fenetre", type=float, default=FENETRE, help="taille des fenêtres en s (défaut : 10)")
    ap.add_argument("--json", help="écrit aussi la mesure dans ce fichier JSON")
    a = ap.parse_args(argv)
    if a.fenetre < 1:
        raise ErreurKit("--fenetre doit valoir au moins 1 s")
    m = mesurer(a.fichier, a.fenetre)
    print(rapport(m))
    if a.json:
        ecrire_json(a.json, m)
        print(f"→ {a.json}")
    return 0


if __name__ == "__main__":
    executer(main)
