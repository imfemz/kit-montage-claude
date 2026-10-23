#!/usr/bin/env python3
"""Applique une cutlist (segments à GARDER) sur la vidéo → rough-cut.mp4.

- Réencode en H.264 (libx264, crf 18) + AAC 320k, moov en tête du fichier.
- Fondu audio de 15 ms de part et d'autre de chaque raccord : pas de clic.
- Les bornes des segments sont recalées sur les limites d'image, pour que le son
  et l'image gardent exactement la même durée à chaque segment.
- Avec --transcript, écrit transcript.cut.json : les mots remappés sur la nouvelle
  timeline. C'est CE fichier qu'il faut utiliser ensuite (sous-titres, marqueurs).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (ErreurKit, ecrire_json, executer, exiger_fichier, fmt_duree, lancer, lire_json,
                    sonder, verifier_outils)

FONDU = 0.015
LIMITE_LIGNE = 100_000      # au-delà, le graphe de filtres passe par un fichier


def caler_sur_images(t: float, fps, decalage: float) -> float:
    if not fps:
        return t
    pas = float(1 / fps)
    return decalage + round((t - decalage) / pas) * pas


def preparer_segments(cutlist: dict, info: dict) -> tuple[list[tuple[float, float]], float]:
    """Segments triés, bornés à la durée de la source et recalés sur les images. Renvoie aussi le décalage max."""
    bruts = cutlist.get("segments")
    if bruts is None:
        bruts = [{"debut": s["start"], "fin": s["end"]} for s in cutlist.get("keep_segments", [])]
    if not bruts:
        raise ErreurKit("la cutlist ne contient aucun segment à garder")
    duree = info["duree"]
    segs, decalage_max = [], 0.0
    for s in sorted(bruts, key=lambda s: float(s["debut"])):
        d, f = float(s["debut"]), float(s["fin"])
        dq = caler_sur_images(d, info["fps"], info["decalage_video"]) if d > 0 else 0.0
        fq = caler_sur_images(f, info["fps"], info["decalage_video"]) if f < duree - 1e-3 else duree
        decalage_max = max(decalage_max, abs(dq - d), abs(fq - f) if f < duree - 1e-3 else 0.0)
        dq, fq = max(0.0, dq), min(duree, fq)
        if segs and dq < segs[-1][1]:
            raise ErreurKit(f"segments qui se chevauchent autour de {d:.3f} s")
        if fq - dq > 1e-3:
            segs.append((dq, fq))
    if not segs:
        raise ErreurKit("aucun segment non vide après recalage")
    return segs, decalage_max


def graphe_filtres(segs: list[tuple[float, float]], info: dict) -> str:
    """trim/atrim par segment + fondus de 15 ms aux raccords + concat."""
    demi = float(1 / info["fps"]) / 4 if info["fps"] else 0.0   # évite l'ambiguïté d'une borne pile sur une image
    n = len(segs)
    parts, entrees = [], []
    for i, (d, f) in enumerate(segs):
        if info["a_video"]:
            vd = max(0.0, d - demi) if d > 0 else 0.0
            vf = f - demi if f < info["duree"] - 1e-3 else f + 1.0
            parts.append(f"[0:v:0]trim=start={vd:.6f}:end={vf:.6f},setpts=PTS-STARTPTS[v{i}]")
            entrees.append(f"[v{i}]")
        if info["a_audio"]:
            longueur = f - d
            fondu = min(FONDU, longueur / 2)
            chaine = f"[0:a:0]atrim=start={d:.6f}:end={f:.6f},asetpts=PTS-STARTPTS"
            if i > 0:
                chaine += f",afade=t=in:st=0:d={fondu:.4f}"
            if i < n - 1:
                chaine += f",afade=t=out:st={longueur - fondu:.6f}:d={fondu:.4f}"
            parts.append(chaine + f"[a{i}]")
            entrees.append(f"[a{i}]")
    v = 1 if info["a_video"] else 0
    a = 1 if info["a_audio"] else 0
    sorties = ("[outv]" if v else "") + ("[outa]" if a else "")
    parts.append("".join(entrees) + f"concat=n={n}:v={v}:a={a}{sorties}")
    return ";\n".join(parts)


def remapper_transcript(tr: dict, segs: list[tuple[float, float]]) -> tuple[dict, int]:
    """Mots entièrement dans un segment gardé, horaires sur la nouvelle timeline. Renvoie (transcript, nb_retirés)."""
    debuts, curseur = [], 0.0
    for d, f in segs:
        debuts.append(curseur)
        curseur += f - d
    mots, retires = [], 0
    for m in tr.get("mots", []):
        d, f = float(m["debut"]), float(m["fin"])
        for (sd, sf), nd in zip(segs, debuts):
            if sd - 1e-6 <= d and f <= sf + 1e-6:
                mots.append({**m, "debut": round(nd + d - sd, 3), "fin": round(nd + f - sd, 3)})
                break
        else:
            retires += 1
    out = {k: v for k, v in tr.items() if k not in ("mots", "duree")}
    out.update({"duree": round(curseur, 3), "timeline": "apres_coupe", "mots": mots})
    return out, retires


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Monte la vidéo selon la cutlist → rough-cut.mp4 (+ transcript remappé).",
        epilog="Exemple : python scripts/couper.py rush.mp4 cutlist.json --transcript transcript.json",
    )
    ap.add_argument("video", help="vidéo d'origine")
    ap.add_argument("cutlist", help="cutlist.json écrit par derush.py")
    ap.add_argument("--sortie", help="vidéo montée (défaut : rough-cut.mp4 à côté de la vidéo)")
    ap.add_argument("--transcript", help="transcript.json d'origine, à remapper sur la nouvelle timeline")
    ap.add_argument("--sortie-transcript", help="défaut : transcript.cut.json à côté de la vidéo montée")
    ap.add_argument("--preset", default="medium", help="preset libx264 (défaut : medium)")
    a = ap.parse_args(argv)

    verifier_outils("ffmpeg", "ffprobe")
    video = exiger_fichier(a.video)
    cutlist = lire_json(a.cutlist)
    info = sonder(video)
    if not info["a_video"] and not info["a_audio"]:
        raise ErreurKit(f"{video.name} ne contient ni image ni son")
    segs, decalage = preparer_segments(cutlist, info)
    sortie = Path(a.sortie) if a.sortie else video.parent / "rough-cut.mp4"
    sortie.parent.mkdir(parents=True, exist_ok=True)

    graphe = graphe_filtres(segs, info)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(video)]
    tmp = None
    if len(graphe) > LIMITE_LIGNE:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(graphe)
        tmp.close()
        cmd += ["-/filter_complex", tmp.name]       # ffmpeg >= 7
    else:
        cmd += ["-filter_complex", graphe]
    if info["a_video"]:
        cmd += ["-map", "[outv]", "-c:v", "libx264", "-crf", "18", "-preset", a.preset, "-pix_fmt", "yuv420p"]
    if info["a_audio"]:
        cmd += ["-map", "[outa]", "-c:a", "aac", "-b:a", "320k"]
    cmd += ["-movflags", "+faststart", str(sortie)]
    print(f"montage de {len(segs)} segments…", file=sys.stderr)
    try:
        lancer(cmd)
    finally:
        if tmp:
            Path(tmp.name).unlink(missing_ok=True)

    attendu = sum(f - d for d, f in segs)
    obtenu = sonder(sortie)["duree"]
    print(f"rough-cut : {len(segs)} segments, {max(0, len(segs) - 1)} raccords, "
          f"{fmt_duree(info['duree'])} → {fmt_duree(obtenu)} (attendu {fmt_duree(attendu)})")
    if decalage > 0.001:
        print(f"note : bornes recalées sur les images (décalage max {decalage * 1000:.0f} ms)")
    if a.transcript:
        tr, retires = remapper_transcript(lire_json(a.transcript), segs)
        sortie_tr = Path(a.sortie_transcript) if a.sortie_transcript else sortie.parent / "transcript.cut.json"
        ecrire_json(sortie_tr, tr)
        print(f"transcript remappé : {len(tr['mots'])} mots, {retires} retirés → {sortie_tr}")
    print(f"→ {sortie}")
    pas = float(1 / info["fps"]) if info["fps"] else 0.05
    if abs(obtenu - attendu) > max(2 * pas, 0.1):
        print(f"attention : durée obtenue {obtenu:.3f} s au lieu de {attendu:.3f} s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    executer(main)
