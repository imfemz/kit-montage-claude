#!/usr/bin/env python3
"""Propose où poser les zooms face cam (44 zooms d'un YouTuber mesurés image par image, 24/10/2026).

Quand :
  - au DÉBUT d'une phrase qui fait tourner le récit : contraste (« mais », « sauf que »…), conséquence (« donc »,
    « du coup »), exemple (« par exemple », « imagine »…), définition (« le rythme, c'est… »), question, accroche ;
    une simple explication n'en a presque jamais ;
  - jamais pour souligner un mot fort : le zoom marque la STRUCTURE, pas l'emphase ;
  - au moins 9 s entre deux zooms ; passé 15 s sans zoom, la phrase suivante en reçoit un (« relance ») ;
  - au moins 7 s après une coupe (posé sur un raccord, il ne se voit pas) et 2 s avant la suivante (jamais de zoom
    sur un plan trop court).
Le geste, toujours le même : 0,85 s, +8,5 %, avant puis arrière en alternance, courbe MOTION.zoom
(cubic-bezier(0.35, 0, 0.27, 1)), avec un whoosh grave un peu long qui démarre avec lui.

  zooms.py transcript.cut.json --cutlist cutlist.json   transcript de la vidéo montée (couper.py --transcript)
  zooms.py transcript.json --cutlist cutlist.json       transcript du rush : les horaires sont remis sur la vidéo montée
Sortie (zooms.json à côté du transcript) : {"zooms": [{"t", "duree", "de", "a", "role", "phrase"}], "coupes": [...]}
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ErreurKit, ecrire_json, executer, lire_json
from derush import _normaliser

DUREE, AMPLITUDE = 0.85, 1.085
ECART_MIN, ECART_MAX = 9.0, 15.0
APRES_COUPE, AVANT_COUPE = 7.0, 2.0
PAUSE_PHRASE = 0.6

MARQUEURS = [
    ("contraste", ["mais", "sauf que", "pourtant", "par contre", "en revanche", "sauf"]),
    ("consequence", ["donc", "du coup", "alors", "résultat", "resultat"]),
    ("exemple", ["par exemple", "imagine", "imaginez", "prenons", "genre"]),
    ("transition", ["maintenant", "bref", "voilà", "voila", "premièrement", "deuxièmement", "numéro", "numero",
                    "première", "premiere", "deuxième", "deuxieme", "troisième", "troisieme"]),
]


def phrases(mots: list[dict], pause: float = PAUSE_PHRASE) -> list[dict]:
    """Découpe en phrases : fin sur . ? ! … ou sur une pause d'au moins `pause` s."""
    out, cour = [], []
    for i, m in enumerate(mots):
        cour.append(m)
        fin_ponct = re.search(r"[.?!…]$", m["mot"].strip())
        pause_ap = i + 1 < len(mots) and mots[i + 1]["debut"] - m["fin"] >= pause
        if fin_ponct or pause_ap or i + 1 == len(mots):
            out.append({"debut": cour[0]["debut"], "fin": cour[-1]["fin"], "texte": " ".join(x["mot"] for x in cour)})
            cour = []
    return out


def role(texte: str, index: int) -> str:
    """Rôle d'une phrase dans le récit ; « explication » = aucun zoom sauf relance."""
    mots = [w for w in (_normaliser(x) for x in texte.split()) if w]
    debut = " ".join(mots[:2])
    for nom, liste in MARQUEURS:
        if any(debut == m or debut.startswith(m + " ") for m in liste):
            return nom
    if texte.strip().endswith("?"):
        return "question"
    if re.match(r"^[^,.?!]{2,40},\s*(c'est|c’est|ça veut dire|ca veut dire)\b", texte.strip(), re.I):
        return "definition"                     # « Le rythme, c'est… » : une définition, pas « ça c'est bien »
    return "accroche" if index == 0 else "explication"


def remapper(mots: list[dict], segments: list[dict]) -> list[dict]:
    """Mots du rush entièrement dans un segment gardé, remis sur la timeline montée."""
    out, curseur = [], 0.0
    bornes = []
    for s in segments:
        bornes.append((s["debut"], s["fin"], curseur)); curseur += s["fin"] - s["debut"]
    for m in mots:
        for d, f, nd in bornes:
            if d - 1e-6 <= m["debut"] and m["fin"] <= f + 1e-6:
                out.append({**m, "debut": round(nd + m["debut"] - d, 3), "fin": round(nd + m["fin"] - d, 3)}); break
    return out


def coupes_montage(segments: list[dict]) -> list[float]:
    """Heures des raccords sur la vidéo montée (fin de chaque segment, sauf le dernier)."""
    t, out = 0.0, []
    for s in segments[:-1]:
        t += s["fin"] - s["debut"]; out.append(round(t, 3))
    return out


def planifier(phr: list[dict], coupes: list[float], fin_video: float) -> list[dict]:
    zooms, dernier, zoome = [], 0.0, False      # le début de la vidéo n'est pas un raccord ; 1re relance après 15 s
    premier = True
    for i, p in enumerate(phr):
        t, r = p["debut"], role(p["texte"], i)
        avant = [c for c in coupes if c <= t]
        apres = [c for c in coupes if c > t] or [fin_video]
        if not premier and t - dernier < ECART_MIN:
            continue
        if avant and t - avant[-1] < APRES_COUPE:
            continue
        if apres[0] - t < AVANT_COUPE:
            continue
        if r == "explication":
            if t - dernier < ECART_MAX:
                continue
            r = "relance"
        de, a = (AMPLITUDE, 1.0) if zoome else (1.0, AMPLITUDE)
        zooms.append({"t": round(t, 3), "duree": DUREE, "de": de, "a": a, "role": r, "phrase": p["texte"][:120]})
        dernier, zoome, premier = t, not zoome, False
    return zooms


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Propose les zooms face cam au début des phrases qui tournent → zooms.json")
    ap.add_argument("transcript", help="transcript.json (rush) ou transcript.cut.json (vidéo montée)")
    ap.add_argument("--cutlist", help="cutlist.json : raccords à éviter (et remappage si le transcript est celui du rush)")
    ap.add_argument("--sortie", help="défaut : zooms.json à côté du transcript")
    a = ap.parse_args(argv)
    tr = lire_json(a.transcript)
    mots = sorted(tr.get("mots", []), key=lambda m: m["debut"])
    if not mots:
        raise ErreurKit("le transcript ne contient aucun mot")
    coupes = []
    if a.cutlist:
        segments = lire_json(a.cutlist).get("segments", [])
        coupes = coupes_montage(segments)
        if tr.get("timeline") != "apres_coupe":
            mots = remapper(mots, segments)
    phr = phrases(mots)
    zooms = planifier(phr, coupes, mots[-1]["fin"])
    sortie = Path(a.sortie) if a.sortie else Path(a.transcript).with_name("zooms.json")
    ecrire_json(sortie, {"zooms": zooms, "coupes": coupes,
                         "regles": {"duree": DUREE, "amplitude": AMPLITUDE, "courbe": "cubic-bezier(0.35, 0, 0.27, 1)",
                                    "ecart_min": ECART_MIN, "ecart_max": ECART_MAX, "apres_coupe": APRES_COUPE}})
    print(f"{len(phr)} phrases, {len(zooms)} zooms proposés (1 toutes les {ECART_MIN:g}-{ECART_MAX:g} s, au début des phrases qui tournent) :")
    for z in zooms:
        sens = "avant" if z["a"] > z["de"] else "arrière"
        print(f"  {z['t']:8.2f} s  {sens:7}  {z['role']:11}  « {z['phrase'][:70]} »")
    print(f"→ {sortie} (chaque zoom : un whoosh grave qui démarre avec lui)")
    return 0


if __name__ == "__main__":
    executer(main)
