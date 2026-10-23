#!/usr/bin/env python3
"""Test des marqueurs : à quel rythme le spectateur reçoit-il une information nouvelle ?

Chaque événement {t, canal, label} est une information nouvelle (un plan qui change,
un texte qui entre, une idée, la musique qui change, un effet sonore, une ambiance).
Les raccords de la cutlist comptent comme canal « image ».
Des événements à moins de --fusion s du premier d'une grappe forment UNE information :
le spectateur ne perçoit qu'un changement.
Un TROU est un intervalle de plus de --trou s sans information nouvelle (le début et la
fin de la vidéo servent de bornes).

Sorties dans --sortie : rapport.txt, marker_test.json, timeline.svg.
Code de sortie : 0 sans trou, 1 s'il reste au moins un trou, 2 en cas d'erreur.

Format d'evenements.json : [{"t": 12.4, "canal": "texte", "label": "titre"}, ...]
(ou {"evenements": [...]}). Les horaires sont ceux de la vidéo MONTÉE.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ErreurKit, ecrire_json, executer, lire_json

CANAUX = ["image", "texte", "idee", "musique", "sfx", "ambiance"]
COULEURS = {"image": "#2f6fdf", "texte": "#d98a1f", "idee": "#2aa36b", "musique": "#8e44ad",
            "sfx": "#d9534f", "ambiance": "#138d9c"}
COULEUR_AUTRE = "#7a7a7a"


# --------------------------------------------------------------------------- données

def charger_evenements(data) -> list[dict]:
    if isinstance(data, dict):
        data = data.get("evenements", data.get("events", []))
    if not isinstance(data, list):
        raise ErreurKit("evenements.json doit contenir une liste d'événements")
    out = []
    for e in data:
        try:
            t = float(e["t"])
        except (KeyError, TypeError, ValueError) as err:
            raise ErreurKit(f"événement sans horaire « t » : {e!r}") from err
        canal = str(e.get("canal", e.get("ch", "autre"))).strip().lower() or "autre"
        out.append({"t": t, "canal": canal, "label": str(e.get("label", ""))})
    return out


def raccords_de_cutlist(cutlist: dict) -> list[dict]:
    """Instants des raccords sur la timeline montée (cumul des durées des segments)."""
    segs = cutlist.get("segments")
    if segs is None:
        segs = [{"debut": s["start"], "fin": s["end"]} for s in cutlist.get("keep_segments", [])]
    out, curseur = [], 0.0
    for i, s in enumerate(sorted(segs, key=lambda s: float(s["debut"]))):
        if i > 0:
            out.append({"t": round(curseur, 3), "canal": "image", "label": f"raccord {i}"})
        curseur += float(s["fin"]) - float(s["debut"])
    return out


def duree_de_cutlist(cutlist: dict) -> float | None:
    if "duree_apres" in cutlist:
        return float(cutlist["duree_apres"])
    segs = cutlist.get("segments")
    if segs:
        return sum(float(s["fin"]) - float(s["debut"]) for s in segs)
    return None


# --------------------------------------------------------------------------- analyse

def fusionner(evenements: list[dict], fusion: float) -> list[dict]:
    """Grappes d'événements à moins de `fusion` s du premier événement de la grappe."""
    infos = []
    for e in sorted(evenements, key=lambda e: e["t"]):
        if infos and e["t"] - infos[-1]["t"] <= fusion + 1e-9:
            infos[-1]["evenements"].append(e)
        else:
            infos.append({"t": e["t"], "evenements": [e]})
    return infos


def analyser(evenements: list[dict], duree: float, fusion: float = 0.4, trou: float = 4.0) -> dict:
    hors = [e for e in evenements if not (0 <= e["t"] <= duree + 1e-6)]
    dedans = [e for e in evenements if 0 <= e["t"] <= duree + 1e-6]
    infos = fusionner(dedans, fusion)

    # Le début de la vidéo vaut une information (l'image apparaît) ; la fin est une borne.
    instants = [i["t"] for i in infos]
    if not instants or instants[0] > fusion:
        instants = [0.0] + instants
    bornes = instants + [duree]
    intervalles = [b - a for a, b in zip(instants, instants[1:])]

    def etiquettes(t):
        for i in infos:
            if abs(i["t"] - t) < 1e-9:
                return ", ".join(f"{e['canal']}:{e['label']}" if e["label"] else e["canal"] for e in i["evenements"])
        return "fin de la vidéo" if abs(t - duree) < 1e-9 else "début de la vidéo"

    trous = [{"debut": round(a, 3), "fin": round(b, 3), "duree": round(b - a, 3),
              "avant": etiquettes(a), "apres": etiquettes(b)}
             for a, b in zip(bornes, bornes[1:]) if b - a > trou + 1e-9]
    par_canal = {}
    for e in dedans:
        par_canal[e["canal"]] = par_canal.get(e["canal"], 0) + 1
    return {
        "duree": round(duree, 3),
        "fusion": fusion,
        "seuil_trou": trou,
        "evenements": len(dedans),
        "evenements_hors_video": len(hors),
        "informations": len(infos),
        "intervalle_median": round(statistics.median(intervalles), 3) if intervalles else None,
        "intervalle_moyen": round(duree / max(1, len(instants)), 3),
        "plus_grand_ecart": round(max(b - a for a, b in zip(bornes, bornes[1:])), 3) if len(bornes) > 1 else round(duree, 3),
        "trous": trous,
        "par_canal": par_canal,
        "liste": [{"t": round(i["t"], 3), "evenements": i["evenements"]} for i in infos],
    }


def rapport(r: dict) -> str:
    L = [f"TEST DES MARQUEURS — durée {r['duree']:.1f} s, fusion {r['fusion']:g} s, seuil de trou {r['seuil_trou']:g} s",
         f"  {r['evenements']} événements → {r['informations']} informations",
         f"  intervalle médian : {r['intervalle_median']:.2f} s" if r["intervalle_median"] is not None
         else "  intervalle médian : — (moins de deux informations)",
         f"  intervalle moyen  : {r['intervalle_moyen']:.2f} s",
         f"  plus grand écart  : {r['plus_grand_ecart']:.2f} s",
         "  par canal : " + (", ".join(f"{k} {v}" for k, v in sorted(r["par_canal"].items())) or "aucun")]
    if r["evenements_hors_video"]:
        L.append(f"  ignorés (hors de 0–{r['duree']:.1f} s) : {r['evenements_hors_video']}")
    L.append(f"  TROUS de plus de {r['seuil_trou']:g} s : {len(r['trous'])}")
    for t in r["trous"]:
        L.append(f"    {t['debut']:7.2f} → {t['fin']:7.2f} s  ({t['duree']:.1f} s)   "
                 f"après [{t['avant'][:60]}]   avant [{t['apres'][:60]}]")
    return "\n".join(L)


# --------------------------------------------------------------------------- SVG

def _pas_graduation(duree: float) -> float:
    for p in (1, 2, 5, 10, 15, 30, 60, 120, 300, 600):
        if duree / p <= 16:
            return p
    return 1200


def svg_timeline(r: dict, largeur: int = 1400) -> str:
    """Timeline : une ligne par canal, une ligne INFORMATIONS, trous surlignés en rouge."""
    evs = [e for i in r["liste"] for e in i["evenements"]]
    presents = {e["canal"] for e in evs}
    lignes = [c for c in CANAUX if c in presents] + sorted(presents - set(CANAUX)) + ["INFORMATIONS"]
    g, d, h_ligne, haut = 130, 30, 34, 84
    bas = haut + h_ligne * len(lignes)
    hauteur = bas + 46
    duree = max(r["duree"], 1e-6)
    x = lambda t: g + (largeur - g - d) * t / duree

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur}" height="{hauteur}" '
         f'viewBox="0 0 {largeur} {hauteur}" font-family="Helvetica, Arial, sans-serif">',
         '<rect width="100%" height="100%" fill="#ffffff"/>']
    titre = (f"{r['informations']} informations · médiane "
             + (f"{r['intervalle_median']:.2f} s" if r["intervalle_median"] is not None else "—")
             + f" · plus grand écart {r['plus_grand_ecart']:.1f} s · {len(r['trous'])} trou(s) &gt; {r['seuil_trou']:g} s")
    o.append(f'<text x="{g}" y="26" font-size="16" font-weight="bold" fill="#111">Test des marqueurs</text>')
    o.append(f'<text x="{g}" y="46" font-size="13" fill="#444">{titre}</text>')
    for t in r["trous"]:
        x0, x1 = x(t["debut"]), x(t["fin"])
        o.append(f'<rect x="{x0:.1f}" y="{haut - 6}" width="{x1 - x0:.1f}" height="{bas - haut + 6}" '
                 f'fill="#ff3b30" fill-opacity="0.13"><title>trou {t["debut"]:.2f} → {t["fin"]:.2f} s</title></rect>')
        o.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{haut - 10}" font-size="11" fill="#c0392b" '
                 f'text-anchor="middle">{t["duree"]:.1f} s</text>')
    pas = _pas_graduation(duree)
    k = 0
    while k * pas <= duree + 1e-9:
        xt = x(k * pas)
        o.append(f'<line x1="{xt:.1f}" y1="{haut - 4}" x2="{xt:.1f}" y2="{bas}" stroke="#e6e6e6" stroke-width="1"/>')
        o.append(f'<text x="{xt:.1f}" y="{bas + 18}" font-size="11" fill="#666" text-anchor="middle">{k * pas:g}</text>')
        k += 1
    o.append(f'<text x="{largeur - d}" y="{bas + 36}" font-size="11" fill="#666" text-anchor="end">secondes</text>')
    for n, canal in enumerate(lignes):
        y = haut + n * h_ligne + h_ligne / 2
        nom = "idée" if canal == "idee" else canal
        o.append(f'<text x="{g - 12}" y="{y + 4:.1f}" font-size="12" fill="#222" text-anchor="end">{escape(nom)}</text>')
        o.append(f'<line x1="{g}" y1="{y:.1f}" x2="{largeur - d}" y2="{y:.1f}" stroke="#f0f0f0" stroke-width="1"/>')
        if canal == "INFORMATIONS":
            for i in r["liste"]:
                xi = x(i["t"])
                lab = escape(" + ".join(e["label"] or e["canal"] for e in i["evenements"]))
                o.append(f'<line x1="{xi:.1f}" y1="{y - 12:.1f}" x2="{xi:.1f}" y2="{y + 12:.1f}" stroke="#111" '
                         f'stroke-width="2"><title>{i["t"]:.2f} s : {lab}</title></line>')
        else:
            coul = COULEURS.get(canal, COULEUR_AUTRE)
            for e in evs:
                if e["canal"] == canal:
                    xe = x(e["t"])
                    o.append(f'<line x1="{xe:.1f}" y1="{y - 10:.1f}" x2="{xe:.1f}" y2="{y + 10:.1f}" stroke="{coul}" '
                             f'stroke-width="1.6"><title>{e["t"]:.2f} s : {escape(e["label"])}</title></line>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Test des marqueurs : rythme des informations nouvelles, trous, timeline SVG.",
        epilog="Exemple : python scripts/marker_test.py --duree 62.4 --cutlist cutlist.json "
               "--evenements evenements.json --sortie rythme/",
    )
    ap.add_argument("--duree", type=float, help="durée de la vidéo montée en s (défaut : lue dans la cutlist)")
    ap.add_argument("--evenements", help="evenements.json : [{t, canal, label}] sur la timeline montée")
    ap.add_argument("--cutlist", help="cutlist.json : ses raccords comptent comme canal « image »")
    ap.add_argument("--fusion", type=float, default=0.4, help="événements fusionnés en une information sous cet écart, en s (défaut : 0.4)")
    ap.add_argument("--trou", type=float, default=4.0, help="écart signalé comme trou, en s (défaut : 4.0)")
    ap.add_argument("--sortie", required=True, help="dossier où écrire rapport.txt, marker_test.json et timeline.svg")
    a = ap.parse_args(argv)

    if a.fusion < 0 or a.trou <= 0:
        raise ErreurKit("--fusion doit être ≥ 0 et --trou > 0")
    evenements = []
    duree = a.duree
    if a.cutlist:
        cl = lire_json(a.cutlist)
        evenements += raccords_de_cutlist(cl)
        if duree is None:
            duree = duree_de_cutlist(cl)
    if a.evenements:
        evenements += charger_evenements(lire_json(a.evenements))
    if duree is None or duree <= 0:
        raise ErreurKit("indique --duree (durée de la vidéo montée, en s) ou une --cutlist")
    if not a.evenements and not a.cutlist:
        print("attention : ni --evenements ni --cutlist : seul le début de la vidéo compte", file=sys.stderr)

    r = analyser(evenements, duree, a.fusion, a.trou)
    texte = rapport(r)
    dossier = Path(a.sortie)
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire_json(dossier / "marker_test.json", r)
    (dossier / "rapport.txt").write_text(texte + "\n", encoding="utf-8")
    (dossier / "timeline.svg").write_text(svg_timeline(r), encoding="utf-8")
    print(texte)
    print(f"→ {dossier / 'rapport.txt'}, {dossier / 'marker_test.json'}, {dossier / 'timeline.svg'}")
    return 1 if r["trous"] else 0


if __name__ == "__main__":
    executer(main)
