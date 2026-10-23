"""Export final : normalisation loudnorm en deux passes + H.264/AAC, puis contrôle.

1. Passe de mesure : loudnorm analyse le son (sonie, true peak, LRA, seuil).
2. Passe de normalisation : loudnorm applique la correction mesurée en mode linéaire vers
   −14 LUFS, true peak −1 dBTP, LRA 11. Le son seul est rendu puis re-mesuré (rapide).
   Si loudnorm ne peut pas rester linéaire (le gain nécessaire ferait dépasser le true
   peak) ou si la mesure sort de ±0,5 LU, on passe à un gain + limiteur suréchantillonné
   (192 kHz), ajusté en quelques itérations jusqu'à tenir la cible.
3. Rendu final avec le filtre retenu : vidéo H.264 (libx264, crf 18, preset slow, yuv420p),
   son AAC 320k à 48 kHz, moov en tête (+faststart).
4. Re-mesure EBU R128 du fichier sorti et écart à la cible : il doit tenir à ±0,5 LU.

Code de sortie : 0 si la sortie est dans la cible, 1 sinon, 2 en cas d'erreur.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ErreurKit, executer, exiger_fichier, fmt_duree, lancer, sonder, verifier_outils
from niveau import CIBLE_LUFS, CIBLE_TP, mesurer, rapport

LRA_CIBLE = 11.0
TOLERANCE_LU = 0.5
VISEE_LU = 0.2              # précision visée par les itérations du limiteur
MARGE_TP = 0.5              # plafond du limiteur sous la cible de true peak (l'AAC ajoute des crêtes)
ITERATIONS = 6
SON_FINAL = ["-c:a", "aac", "-b:a", "320k", "-ar", "48000"]


def _json_loudnorm(stderr: str) -> dict:
    debut, fin = stderr.rfind("{"), stderr.rfind("}")
    if debut < 0 or fin < debut:
        raise ErreurKit("loudnorm n'a pas renvoyé de mesure JSON")
    try:
        return json.loads(stderr[debut:fin + 1])
    except json.JSONDecodeError as e:
        raise ErreurKit(f"mesure loudnorm illisible : {e}") from e


def mesure_loudnorm(chemin: Path, cible: float, tp: float, lra: float) -> dict:
    proc = lancer(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-vn", "-sn", "-dn", "-i", str(chemin),
                   "-map", "0:a:0", "-af", f"loudnorm=I={cible}:TP={tp}:LRA={lra}:print_format=json",
                   "-f", "null", "-"])
    m = _json_loudnorm(proc.stderr)
    if not math.isfinite(float(m["input_i"])) or float(m["input_i"]) < -70:
        raise ErreurKit("la piste audio est silencieuse : rien à normaliser")
    return m


def filtre_loudnorm(m: dict, cible: float, tp: float, lra: float) -> str:
    return (f"loudnorm=I={cible}:TP={tp}:LRA={lra}"
            f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
            f":offset={m['target_offset']}:linear=true:print_format=json,aresample=48000")


def filtre_limiteur(gain_db: float, plafond_db: float) -> str:
    limite = min(1.0, max(0.0625, 10 ** (plafond_db / 20)))
    return (f"aformat=sample_fmts=flt,volume={gain_db:.3f}dB,aresample=192000,"
            f"alimiter=limit={limite:.5f}:attack=5:release=50:level=false:latency=true,aresample=48000")


def essai_audio(video: Path, filtre: str, dossier: Path) -> tuple[dict, str]:
    """Rend le son seul avec `filtre` (AAC, comme le rendu final) et le mesure."""
    tmp = dossier / "essai.m4a"
    proc = lancer(["ffmpeg", "-nostdin", "-y", "-hide_banner", "-nostats", "-vn", "-sn", "-dn", "-i", str(video),
                   "-map", "0:a:0", "-af", filtre, *SON_FINAL, str(tmp)])
    return mesurer(tmp), proc.stderr


def dans_la_cible(m: dict, cible: float, tp: float, tolerance: float) -> bool:
    return (m["integree_lufs"] is not None and abs(m["integree_lufs"] - cible) <= tolerance
            and m["true_peak_dbtp"] is not None and m["true_peak_dbtp"] <= tp + 0.05)


def choisir_filtre(video: Path, m1: dict, cible: float, tp: float) -> tuple[str, str, dict]:
    """Renvoie (filtre, méthode, mesure du son rendu avec ce filtre)."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        filtre = filtre_loudnorm(m1, cible, tp, LRA_CIBLE)
        m, err = essai_audio(video, filtre, d)
        mode = _json_loudnorm(err).get("normalization_type", "?")
        if mode == "linear" and dans_la_cible(m, cible, tp, TOLERANCE_LU):
            return filtre, "loudnorm linéaire (2 passes)", m
        print(f"  loudnorm seul : {m['integree_lufs']} LUFS, true peak {m['true_peak_dbtp']} dBTP "
              f"(mode {mode}) → gain + limiteur", file=sys.stderr)

        gain = cible - float(m1["input_i"])
        plafond = tp - MARGE_TP
        meilleur, precedent = None, None
        for n in range(1, ITERATIONS + 1):
            filtre = filtre_limiteur(gain, plafond)
            m, _ = essai_audio(video, filtre, d)
            ecart = m["integree_lufs"] - cible
            print(f"  essai {n} : gain {gain:+.2f} dB, plafond {plafond:.2f} dBFS → "
                  f"{m['integree_lufs']} LUFS, true peak {m['true_peak_dbtp']} dBTP", file=sys.stderr)
            cle = (not dans_la_cible(m, cible, tp, TOLERANCE_LU), abs(ecart))
            if meilleur is None or cle < meilleur[0]:
                meilleur = (cle, filtre, m)
            if dans_la_cible(m, cible, tp, VISEE_LU):
                break
            # le limiteur absorbe une partie du gain : pente estimée sur les deux derniers essais
            pente = 1.0
            if precedent is not None and abs(gain - precedent[0]) > 1e-3:
                pente = min(1.0, max(0.15, (m["integree_lufs"] - precedent[1]) / (gain - precedent[0])))
            precedent = (gain, m["integree_lufs"])
            gain -= ecart / pente
            if m["true_peak_dbtp"] > tp:
                plafond -= (m["true_peak_dbtp"] - tp) + 0.1
        return meilleur[1], "gain + limiteur true peak", meilleur[2]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Export final normalisé (−14 LUFS, −1 dBTP) en H.264 + AAC, avec contrôle de la sortie.",
        epilog="Exemple : python scripts/exporter.py rough-cut.mp4 --sortie exports/final.mp4",
    )
    ap.add_argument("video", help="vidéo à exporter")
    ap.add_argument("--sortie", help="fichier final (défaut : final.mp4 à côté de la vidéo)")
    ap.add_argument("--cible", type=float, default=CIBLE_LUFS, help="sonie intégrée visée en LUFS (défaut : -14)")
    ap.add_argument("--true-peak", type=float, default=CIBLE_TP, help="true peak maximal en dBTP (défaut : -1)")
    ap.add_argument("--preset", default="slow", help="preset libx264 (défaut : slow)")
    ap.add_argument("--crf", type=int, default=18, help="qualité libx264, plus bas = meilleur (défaut : 18)")
    a = ap.parse_args(argv)

    verifier_outils("ffmpeg", "ffprobe")
    video = exiger_fichier(a.video)
    sortie = Path(a.sortie) if a.sortie else video.parent / "final.mp4"
    if sortie.resolve() == video.resolve():
        raise ErreurKit("la sortie doit être différente de l'entrée")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    info = sonder(video)
    if not info["a_audio"]:
        raise ErreurKit(f"{video.name} n'a pas de piste audio : rien à normaliser")

    t0 = time.time()
    print("1/3 mesure de la sonie (loudnorm)…", file=sys.stderr)
    m1 = mesure_loudnorm(video, a.cible, a.true_peak, LRA_CIBLE)
    print(f"  entrée : {float(m1['input_i']):.1f} LUFS, true peak {float(m1['input_tp']):.1f} dBTP, "
          f"LRA {float(m1['input_lra']):.1f} LU", file=sys.stderr)

    print("2/3 normalisation du son…", file=sys.stderr)
    filtre, methode, _ = choisir_filtre(video, m1, a.cible, a.true_peak)

    print("3/3 rendu final…", file=sys.stderr)
    cmd = ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-nostats", "-i", str(video)]
    if info["a_video"]:
        cmd += ["-map", "0:v:0", "-c:v", "libx264", "-crf", str(a.crf), "-preset", a.preset,
                "-pix_fmt", "yuv420p"]
    cmd += ["-map", "0:a:0", "-af", filtre, *SON_FINAL, "-movflags", "+faststart", str(sortie)]
    lancer(cmd)

    controle = mesurer(sortie)
    print(rapport(controle))
    i, tp = controle["integree_lufs"], controle["true_peak_dbtp"]
    ecart = i - a.cible if i is not None else float("inf")
    ok = dans_la_cible(controle, a.cible, a.true_peak, TOLERANCE_LU)
    print(f"export : {float(m1['input_i']):.1f} → {i} LUFS (écart à la cible {ecart:+.2f} LU, "
          f"tolérance ±{TOLERANCE_LU:g}), true peak {tp} dBTP, méthode : {methode}, "
          f"en {fmt_duree(time.time() - t0)}")
    print(f"→ {sortie}")
    if not ok:
        print("hors cible : vérifie la mesure ci-dessus avant de livrer.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    executer(main)
