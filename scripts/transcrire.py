#!/usr/bin/env python3
"""Transcrit une vidéo mot à mot avec faster-whisper.

Sortie (transcript.json) :
    {"source": "rush.mp4", "langue": "fr", "modele": "small", "duree": 812.4,
     "mots": [{"mot": "Bonjour", "debut": 0.52, "fin": 0.91, "proba": 0.98}, ...]}

Les horaires sont en secondes sur la timeline de la vidéo d'origine.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ErreurKit, ecrire_json, executer, exiger_fichier, fmt_duree, sonder, verifier_outils


def transcrire(chemin: Path, langue: str | None, modele: str, appareil: str, calcul: str) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ErreurKit("faster-whisper n'est pas installé : pip install -r requirements.txt") from e

    print(f"chargement du modèle « {modele} » ({appareil}, {calcul})…", file=sys.stderr)
    model = WhisperModel(modele, device=appareil, compute_type=calcul)
    segments, info = model.transcribe(
        str(chemin),
        language=langue,
        word_timestamps=True,
        vad_filter=False,          # on garde tous les mots, même hésitants : le dérush ne retire rien
        condition_on_previous_text=False,
    )
    mots = []
    for seg in segments:
        for w in seg.words or []:
            texte = w.word.strip()
            if not texte:
                continue
            mots.append({
                "mot": texte,
                "debut": round(float(w.start), 3),
                "fin": round(float(w.end), 3),
                "proba": round(float(w.probability), 3),
            })
        print(f"  {fmt_duree(seg.end)} / {fmt_duree(info.duration)}", end="\r", file=sys.stderr)
    print(file=sys.stderr)
    return {
        "source": chemin.name,
        "langue": info.language,
        "modele": modele,
        "duree": round(float(info.duration), 3),
        "mots": mots,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Transcrit une vidéo mot à mot (faster-whisper) → transcript.json.",
        epilog="Exemple : python scripts/transcrire.py projets/ma-video/rush.mp4 --langue fr",
    )
    ap.add_argument("video", help="vidéo ou fichier audio à transcrire")
    ap.add_argument("--langue", default="fr", help="code de langue (fr, en…) ; « auto » pour la détection (défaut : fr)")
    ap.add_argument("--modele", default="small",
                    help="modèle Whisper : tiny, base, small, medium, large-v3… (défaut : small)")
    ap.add_argument("--sortie", help="fichier de sortie (défaut : transcript.json à côté de la vidéo)")
    ap.add_argument("--appareil", default="auto", help="cpu, cuda ou auto (défaut : auto)")
    ap.add_argument("--calcul", default="int8", help="type de calcul faster-whisper (défaut : int8)")
    a = ap.parse_args(argv)

    verifier_outils("ffmpeg", "ffprobe")
    video = exiger_fichier(a.video)
    if not sonder(video)["a_audio"]:
        raise ErreurKit(f"{video.name} n'a pas de piste audio")
    sortie = Path(a.sortie) if a.sortie else video.parent / "transcript.json"
    langue = None if a.langue == "auto" else a.langue

    t0 = time.time()
    data = transcrire(video, langue, a.modele, a.appareil, a.calcul)
    ecrire_json(sortie, data)

    n = len(data["mots"])
    douteux = sum(1 for m in data["mots"] if m["proba"] < 0.5)
    print(f"transcrit : {n} mots sur {fmt_duree(data['duree'])} (langue {data['langue']}, "
          f"{douteux} mots à faible confiance) en {fmt_duree(time.time() - t0)}")
    print(f"→ {sortie}")
    if n == 0:
        print("attention : aucun mot reconnu (piste muette ou langue incorrecte ?)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    executer(main)
