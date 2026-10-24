#!/usr/bin/env python3
"""Vérifie une coupe qui retire un mot en tête de phrase (« Et », « Euh », « Alors »…) en l'ÉCOUTANT.

Couper un « Et » collé à la suite, au jugé ou au creux d'énergie le plus bas, rate une fois sur deux : soit on
garde la fin du « Et », soit on mange le début du mot suivant. La seule preuve, c'est de re-transcrire le son
à partir du point de coupe : si le premier mot entendu est le bon, la coupe est propre.

  verifier_coupe.py rush.mp4 132.80 donc
      re-transcrit 1,4 s à partir de 132,80 s ; OK (code 0) si le premier mot entendu est « donc », ÉCHEC (code 1) sinon.
  verifier_coupe.py rush.mp4 132.71 donc --chercher
      essaie les creux d'énergie entre 132,71 + 0,12 s et 132,71 + 0,8 s, dans l'ordre, et donne le premier point
      de coupe où l'on entend bien « donc ». Aucun ne passe : la coupe n'est pas faisable, il faut une autre prise.

Les mots sont comparés sans majuscules ni ponctuation. Le modèle par défaut (small) suffit pour un mot isolé ;
--modele large-v3 est plus sûr sur une voix rapide.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import OK, VERIFICATION_ECHOUEE, ErreurKit, decoder_audio, executer, exiger_fichier, verifier_outils
from derush import PAS, SR, _normaliser, rms_par_fenetre

ECOUTE = 1.4      # durée re-transcrite à partir du point de coupe (s)
BOURRE = 0.5      # silence ajouté avant et après l'extrait : Whisper entend mieux un mot isolé


def transcripteur(modele: str = "small", langue: str = "fr"):
    """Rend une fonction (audio mono float32 16 kHz) → texte, avec faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ErreurKit("faster-whisper n'est pas installé : pip install -r requirements.txt") from e
    m = WhisperModel(modele, device="cpu", compute_type="int8")

    def transcrire(audio: np.ndarray, sr: int) -> str:
        segs, _ = m.transcribe(audio, language=langue, beam_size=5, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs)
    return transcrire


def premier_mot(audio: np.ndarray, sr: int, t: float, transcrire, duree: float = ECOUTE) -> str:
    """Premier mot entendu dans [t, t + duree], normalisé ('' si rien)."""
    i0, i1 = max(0, int(round(t * sr))), min(len(audio), int(round((t + duree) * sr)))
    extrait = np.pad(audio[i0:i1].astype(np.float32), int(BOURRE * sr))
    for brut in transcrire(extrait, sr).split():
        mot = _normaliser(brut)
        if mot:
            return mot
    return ""


def creux(db: np.ndarray, de: float, pas: float = PAS, apres=(0.12, 0.8)) -> list[float]:
    """Minimums locaux d'énergie entre de + 0,12 s et de + 0,8 s, dans l'ordre du temps (au moins 30 ms d'écart)."""
    i0, i1 = int(round((de + apres[0]) / pas)), min(len(db) - 1, int(round((de + apres[1]) / pas)))
    out: list[float] = []
    for i in range(max(1, i0), i1):
        if db[i] <= db[i - 1] and db[i] <= db[i + 1] and (not out or i * pas - out[-1] >= 0.03):
            out.append(round(i * pas, 3))
    return out


def chercher(audio: np.ndarray, sr: int, db: np.ndarray, de: float, attendu: str, transcrire) -> tuple[float | None, list]:
    """Premier creux d'énergie après `de` où l'on entend `attendu` en premier. Rend (point de coupe ou None, essais)."""
    cible, essais = _normaliser(attendu), []
    for t in creux(db, de):
        mot = premier_mot(audio, sr, t, transcrire)
        essais.append((t, mot))
        if mot == cible:
            return t, essais
    return None, essais


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vérifie à l'oreille (re-transcription) qu'une coupe tombe juste avant le bon mot.")
    ap.add_argument("video", help="vidéo ou audio d'origine")
    ap.add_argument("t", type=float, help="point de coupe (s) ; avec --chercher : début du souffle à nettoyer")
    ap.add_argument("attendu", help="le mot qu'on doit entendre en premier après la coupe")
    ap.add_argument("--chercher", action="store_true", help="cherche le premier creux d'énergie qui passe")
    ap.add_argument("--modele", default="small", help="modèle Whisper (défaut : small ; large-v3 = plus sûr)")
    ap.add_argument("--langue", default="fr")
    a = ap.parse_args(argv)

    verifier_outils("ffmpeg")
    audio = decoder_audio(exiger_fichier(a.video), SR)
    transcrire = transcripteur(a.modele, a.langue)
    if a.chercher:
        t, essais = chercher(audio, SR, rms_par_fenetre(audio, SR), a.t, a.attendu, transcrire)
        for ti, mot in essais:
            print(f"  {ti:9.3f} s → « {mot} »")
        if t is None:
            print(f"ÉCHEC : aucun creux après {a.t:.2f} s ne commence par « {a.attendu} » ; coupe impossible, il faut une autre prise")
            return VERIFICATION_ECHOUEE
        print(f"OK : couper à {t:.3f} s, on entend « {a.attendu} » en premier")
        return OK
    mot = premier_mot(audio, SR, a.t, transcrire)
    if mot == _normaliser(a.attendu):
        print(f"OK : à {a.t:.3f} s, le premier mot entendu est « {mot} »")
        return OK
    print(f"ÉCHEC : à {a.t:.3f} s, on entend « {mot or '(rien)'} » au lieu de « {a.attendu} »")
    return VERIFICATION_ECHOUEE


if __name__ == "__main__":
    executer(main)
