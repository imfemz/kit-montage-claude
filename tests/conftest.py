"""Fixtures communes : signaux synthétiques générés à la volée (aucun média commité)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

ffmpeg_requis = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                   reason="ffmpeg/ffprobe absents du PATH")


def ecrire_wav(chemin: Path, signal: np.ndarray, sr: int) -> Path:
    """Écrit un signal mono float (−1..1) en WAV 16 bits."""
    pcm = np.clip(signal, -1, 1)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


def creer_video(chemin: Path, wav: Path, fps: int = 25) -> Path:
    """Petite vidéo de mire (320×240) qui porte l'audio donné, à la durée de l'audio."""
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={fps}",
                    "-i", str(wav), "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(chemin)], check=True)
    return chemin


def voix_synthetique(duree: float, mots: list[tuple[float, float]], sr: int = 16000, amp: float = 0.3,
                     bruit: float = 0.003, graine: int = 0) -> np.ndarray:
    """Bruit de fond faible + un « mot » (son harmonique modulé) sur chaque intervalle donné."""
    rng = np.random.default_rng(graine)
    n = int(round(duree * sr))
    t = np.arange(n) / sr
    x = bruit * rng.standard_normal(n)
    for d, f in mots:
        i0, i1 = int(d * sr), int(f * sr)
        tt = t[i0:i1]
        env = np.clip(np.sin(np.pi * (tt - d) / (f - d)), 0, 1) ** 0.3
        x[i0:i1] += amp * env * (np.sin(2 * np.pi * 180 * tt) + 0.5 * np.sin(2 * np.pi * 360 * tt)
                                 + 0.25 * np.sin(2 * np.pi * 900 * tt)) / 1.75
    return x


@pytest.fixture
def dossier(tmp_path):
    return tmp_path
