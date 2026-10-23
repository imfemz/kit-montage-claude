"""Outils partagés par les scripts du kit : appels ffmpeg/ffprobe, décodage audio, JSON.

Aucun script ne dépend d'autre chose que de Python >= 3.10, numpy et des binaires
ffmpeg / ffprobe accessibles dans le PATH.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

# Textes d'argparse en français (usage, aide, erreurs de ligne de commande).
_TRADUCTIONS = {
    "usage: ": "utilisation : ",
    "positional arguments": "arguments",
    "options": "options",
    "show this help message and exit": "affiche cette aide et quitte",
    "%(prog)s: error: %(message)s\n": "%(prog)s : erreur : %(message)s\n",
    "the following arguments are required: %s": "arguments obligatoires manquants : %s",
    "unrecognized arguments: %s": "arguments inconnus : %s",
    "argument %(argument_name)s: %(message)s": "argument %(argument_name)s : %(message)s",
    "invalid %(type)s value: %(value)r": "valeur invalide (%(type)s attendu) : %(value)r",
    "expected one argument": "une valeur attendue",
}
argparse._ = lambda texte: _TRADUCTIONS.get(texte, texte)

# Codes de sortie communs à tous les scripts.
OK = 0
VERIFICATION_ECHOUEE = 1   # le script a tourné, mais le résultat ne passe pas le contrôle
ERREUR = 2                 # entrée invalide, fichier absent, ffmpeg en échec...


class ErreurKit(Exception):
    """Erreur attendue (entrée invalide, outil absent) : message clair, pas de trace Python."""


def verifier_outils(*noms: str) -> None:
    manquants = [n for n in (noms or ("ffmpeg", "ffprobe")) if shutil.which(n) is None]
    if manquants:
        raise ErreurKit(
            f"introuvable dans le PATH : {', '.join(manquants)}. "
            "Installe ffmpeg (macOS : brew install ffmpeg ; Linux : apt install ffmpeg)."
        )


def lancer(cmd: list[str], *, binaire: bool = False) -> subprocess.CompletedProcess:
    """Lance une commande ; en cas d'échec, lève ErreurKit avec la fin de stderr."""
    proc = subprocess.run(cmd, capture_output=True, text=not binaire)
    if proc.returncode != 0:
        err = proc.stderr if isinstance(proc.stderr, str) else proc.stderr.decode("utf-8", "replace")
        fin = "\n".join(err.strip().splitlines()[-12:])
        raise ErreurKit(f"{Path(cmd[0]).name} a échoué (code {proc.returncode}) :\n{fin}")
    return proc


def exiger_fichier(chemin: str | Path) -> Path:
    p = Path(chemin)
    if not p.is_file():
        raise ErreurKit(f"fichier introuvable : {chemin}")
    return p


def sonder(chemin: str | Path) -> dict:
    """Infos utiles d'un média : durée, présence audio/vidéo, cadence et décalage du flux vidéo."""
    verifier_outils("ffprobe")
    proc = lancer(["ffprobe", "-v", "error", "-print_format", "json",
                   "-show_format", "-show_streams", str(chemin)])
    data = json.loads(proc.stdout)
    flux = data.get("streams", [])
    video = next((s for s in flux if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in flux if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    duree = float(fmt.get("duration") or 0.0)
    if duree <= 0:
        durees = [float(s["duration"]) for s in flux if s.get("duration")]
        duree = max(durees) if durees else 0.0

    fps = None
    decalage_video = 0.0
    if video is not None:
        for cle in ("avg_frame_rate", "r_frame_rate"):
            val = video.get(cle, "0/0")
            try:
                f = Fraction(val)
            except (ValueError, ZeroDivisionError):
                continue
            if 0 < f < 1000:
                fps = f
                break
        try:
            decalage_video = float(video.get("start_time", 0)) - float(fmt.get("start_time", 0))
        except (TypeError, ValueError):
            decalage_video = 0.0
    return {
        "duree": duree,
        "a_audio": audio is not None,
        "a_video": video is not None,
        "fps": fps,                         # Fraction (ex. 24000/1001) ou None
        "decalage_video": max(0.0, decalage_video),
        "largeur": video.get("width") if video else None,
        "hauteur": video.get("height") if video else None,
    }


def decoder_audio(chemin: str | Path, sr: int = 16000):
    """Décode la piste audio en mono float32 à `sr` Hz (numpy.ndarray)."""
    import numpy as np

    verifier_outils("ffmpeg")
    proc = lancer(["ffmpeg", "-nostdin", "-v", "error", "-vn", "-sn", "-dn", "-i", str(chemin),
                   "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], binaire=True)
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def lire_json(chemin: str | Path):
    p = exiger_fichier(chemin)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErreurKit(f"JSON invalide dans {p.name} : {e}") from e


def ecrire_json(chemin: str | Path, data) -> Path:
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def fmt_duree(s: float) -> str:
    """12.3 -> '12,3 s' ; 83.4 -> '1 min 23,4 s'."""
    m, r = divmod(s, 60)
    if m:
        return f"{int(m)} min {r:04.1f} s".replace(".", ",")
    return f"{r:.1f} s".replace(".", ",")


def executer(main) -> None:
    """Point d'entrée commun : traduit les erreurs attendues en message + code de sortie 2."""
    try:
        code = main()
    except ErreurKit as e:
        print(f"erreur : {e}", file=sys.stderr)
        code = ERREUR
    except KeyboardInterrupt:
        print("interrompu.", file=sys.stderr)
        code = 130
    sys.exit(code or OK)
