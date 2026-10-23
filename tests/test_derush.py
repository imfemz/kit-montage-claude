"""Dérush : coupes au creux d'énergie, jamais dans un mot, aucun mot retiré."""

from __future__ import annotations

import json
from fractions import Fraction

import numpy as np
import pytest

from conftest import creer_video, ecrire_wav, ffmpeg_requis, voix_synthetique

import couper
import derush
from derush import Grille, planifier, reprises_possibles, rms_par_fenetre, verifier_coupes

SR = 16000
MARGE = 0.040


def _mots(intervalles):
    return [{"mot": f"m{i}", "debut": d, "fin": f, "proba": 1.0} for i, (d, f) in enumerate(intervalles)]


def _coupes(segments, duree):
    bornes = {s["debut"] for s in segments} | {s["fin"] for s in segments}
    return sorted(c for c in bornes if 1e-6 < c < duree - 1e-6)


def test_coupe_au_creux_d_energie():
    """Deux creux quasi muets placés dans le blanc : les deux coupes doivent tomber dedans."""
    intervalles = [(0.5, 1.0), (1.2, 1.6), (4.0, 4.5)]
    x = voix_synthetique(5.0, intervalles, sr=SR, bruit=0.01)
    rng = np.random.default_rng(1)
    i0, i1 = int(2.5 * SR), int(3.2 * SR)
    x[i0:i1] += 0.02 * rng.standard_normal(i1 - i0)            # une respiration (≈ 17 dB sous la voix)
    for d, f in [(1.70, 1.73), (3.82, 3.85)]:                  # deux creux (quasi silence)
        x[int(d * SR):int(f * SR)] *= 0.01
    db = rms_par_fenetre(x.astype(np.float32), SR)

    segments, raccourcis, _ = planifier(_mots(intervalles), 5.0, db, Grille(), 1.0, 0.25, MARGE)

    milieu = [r for r in raccourcis if r["sorte"] == "milieu"]
    assert len(milieu) == 1, "seul le blanc de 2,4 s doit être raccourci (pas celui de 0,2 s)"
    c1, c2 = milieu[0]["coupe"]
    assert 1.70 <= c1 <= 1.73, c1
    assert 3.82 <= c2 <= 3.85, c2
    assert 0.25 * 0.7 - 1e-9 <= milieu[0]["garde"] <= 0.25 * 1.5 + 1e-9
    assert verifier_coupes(segments, _mots(intervalles), MARGE, 5.0) == []


def test_creux_plus_bas_que_le_bruit_de_fond_mais_contre_un_mot():
    """Le silence le plus profond touche le mot : la coupe doit quand même rester à ≥ 40 ms du mot."""
    intervalles = [(0.3, 1.0), (3.0, 3.6)]
    x = voix_synthetique(4.0, intervalles, sr=SR, bruit=0.02)
    x[int(1.0 * SR):int(1.035 * SR)] = 0.0       # silence total collé à la fin du mot
    x[int(2.965 * SR):int(3.0 * SR)] = 0.0       # silence total collé au début du mot suivant
    db = rms_par_fenetre(x.astype(np.float32), SR)
    segments, _, _ = planifier(_mots(intervalles), 4.0, db, Grille(), 1.0, 0.25, MARGE)
    for c in _coupes(segments, 4.0):
        for d, f in intervalles:
            assert c <= d - MARGE + 1e-9 or c >= f + MARGE - 1e-9, (c, d, f)


@pytest.mark.parametrize("graine", range(12))
def test_propriete_jamais_dans_un_mot_et_aucun_mot_retire(graine):
    rng = np.random.default_rng(graine)
    t, intervalles = 0.2 + rng.uniform(0, 1.5), []
    while t < 50:
        d = rng.uniform(0.08, 0.6)
        intervalles.append((round(t, 3), round(t + d, 3)))
        t += d + (rng.uniform(0.0, 0.3) if rng.random() < 0.7 else rng.uniform(0.6, 3.5))
    duree = t + rng.uniform(0, 2)
    x = voix_synthetique(duree, intervalles, sr=SR, bruit=0.01, graine=graine)
    db = rms_par_fenetre(x.astype(np.float32), SR)
    grille = Grille(Fraction(30000, 1001)) if graine % 2 else Grille()
    mots = _mots(intervalles)
    segments, raccourcis, _ = planifier(mots, duree, db, grille, 1.0, 0.25, MARGE)

    assert verifier_coupes(segments, mots, MARGE, duree) == []
    # chaque blanc ≥ 1 s est raccourci, chaque blanc plus court est intact
    longs = sum(1 for (a, _), (b, _) in zip([(0, 0)] + [(f, 0) for _, f in intervalles],
                                             [(d, 0) for d, _ in intervalles] + [(duree, 0)]) if b - a >= 1.0)
    assert len(raccourcis) == longs
    for r in raccourcis:
        assert r["garde"] <= 0.25 * 1.5 + 1e-6
    # les segments ne se chevauchent pas et sont dans l'ordre
    for s1, s2 in zip(segments, segments[1:]):
        assert s1["fin"] < s2["debut"]


def test_blanc_avec_du_son_non_transcrit_n_est_pas_coupe():
    """Un « mot » que la transcription a manqué (ou de la musique) dans un blanc : on ne coupe pas."""
    intervalles = [(0.5, 1.0), (4.0, 4.5)]
    x = voix_synthetique(5.0, intervalles + [(2.2, 2.7)], sr=SR, bruit=0.01)   # 2,2-2,7 : mot non transcrit
    db = rms_par_fenetre(x.astype(np.float32), SR)
    segments, raccourcis, sonores = planifier(_mots(intervalles), 5.0, db, Grille(), 1.0, 0.25, MARGE)
    assert all(r["sorte"] != "milieu" for r in raccourcis)
    assert [(b["debut"], b["fin"]) for b in sonores] == [(1.0, 4.0)]
    assert any(s["debut"] <= 2.2 and 2.7 <= s["fin"] for s in segments)
    # avec l'option explicite, le blanc est raccourci quand même
    _, raccourcis2, sonores2 = planifier(_mots(intervalles), 5.0, db, Grille(), 1.0, 0.25, MARGE,
                                         couper_blancs_sonores=True)
    assert sonores2 == [] and any(r["sorte"] == "milieu" for r in raccourcis2)


def test_coupes_sur_limites_d_image():
    intervalles = [(0.5, 1.0), (3.0, 3.5)]
    x = voix_synthetique(4.0, intervalles, sr=SR)
    db = rms_par_fenetre(x.astype(np.float32), SR)
    segments, _, _ = planifier(_mots(intervalles), 4.0, db, Grille(Fraction(25)), 1.0, 0.25, MARGE)
    for c in _coupes(segments, 4.0):
        assert abs(c * 25 - round(c * 25)) < 1e-6, c


def test_reprises_possibles():
    phrase = "je vais vous montrer euh je vais vous montrer comment faire".split()
    mots = [{"mot": w, "debut": i * 0.4, "fin": i * 0.4 + 0.3} for i, w in enumerate(phrase)]
    r = reprises_possibles(mots)
    assert len(r) == 1
    assert r[0]["mots"] == 4 and r[0]["texte"] == "je vais vous montrer"
    assert r[0]["si_valide_couper"] == {"debut": 0.0, "fin": 2.0}

    loin = [{**m, "debut": m["debut"] + (20 if i >= 5 else 0), "fin": m["fin"] + (20 if i >= 5 else 0)}
            for i, m in enumerate(mots)]
    assert reprises_possibles(loin) == []
    deux = [{"mot": w, "debut": i * 0.4, "fin": i * 0.4 + 0.3} for i, w in enumerate("on a dit on a".split())]
    assert reprises_possibles(deux) == []


@ffmpeg_requis
def test_bout_en_bout_derush_puis_couper(dossier):
    intervalles = [(0.6, 1.4), (1.6, 2.4), (5.0, 5.8), (6.0, 6.6)]
    duree = 8.0
    wav = ecrire_wav(dossier / "voix.wav", voix_synthetique(duree, intervalles, sr=48000), 48000)
    video = creer_video(dossier / "rush.mp4", wav, fps=25)
    (dossier / "transcript.json").write_text(json.dumps({"mots": _mots(intervalles), "duree": duree}))

    assert derush.main([str(video), str(dossier / "transcript.json")]) == 0
    cl = json.loads((dossier / "cutlist.json").read_text())
    assert len(cl["blancs_raccourcis"]) == 2          # 2,4 → 5,0 et 6,6 → 8,0 (le début 0,6 s est court)
    assert verifier_coupes(cl["segments"], _mots(intervalles), MARGE, cl["duree_source"]) == []

    assert couper.main([str(video), str(dossier / "cutlist.json"),
                        "--transcript", str(dossier / "transcript.json")]) == 0
    from commun import sonder
    sortie = sonder(dossier / "rough-cut.mp4")
    assert abs(sortie["duree"] - cl["duree_apres"]) <= 0.08
    tr = json.loads((dossier / "transcript.cut.json").read_text())
    assert len(tr["mots"]) == len(intervalles)
    # le 3e mot recule exactement de la durée retirée avant lui
    retire = 5.0 - 2.4 - cl["blancs_raccourcis"][0]["garde"]
    assert tr["mots"][2]["debut"] == pytest.approx(5.0 - retire, abs=0.002)


def test_remappage_transcript():
    tr = {"mots": [{"mot": "a", "debut": 0.5, "fin": 0.9}, {"mot": "b", "debut": 3.0, "fin": 3.4}]}
    out, retires = couper.remapper_transcript(tr, [(0.0, 1.2), (2.8, 4.0)])
    assert retires == 0
    assert out["mots"][1]["debut"] == pytest.approx(1.2 + 0.2)
    assert out["duree"] == pytest.approx(2.4)


@ffmpeg_requis
def test_couper_beaucoup_de_segments_image_et_son_restent_synchrones(dossier):
    """20 segments : la vidéo et le son du rough-cut doivent garder la même durée (pas de dérive)."""
    import subprocess

    wav = ecrire_wav(dossier / "v.wav", voix_synthetique(12.0, [(0.5, 11.5)], sr=48000), 48000)
    video = creer_video(dossier / "rush.mp4", wav, fps=25)
    rng = np.random.default_rng(7)
    bornes = np.sort(rng.choice(np.arange(1, 290), size=40, replace=False)) * 0.04 + 0.013  # hors grille exprès
    segments = [{"debut": float(a), "fin": float(b)} for a, b in zip(bornes[::2], bornes[1::2])]
    (dossier / "cut.json").write_text(json.dumps({"segments": segments}))
    assert couper.main([str(video), str(dossier / "cut.json"), "--sortie", str(dossier / "rc.mp4"),
                        "--preset", "ultrafast"]) == 0
    sortie = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration",
                             "-of", "json", str(dossier / "rc.mp4")], capture_output=True, text=True).stdout
    durees = {s["codec_type"]: float(s["duration"]) for s in json.loads(sortie)["streams"]}
    attendu = sum(round(s["fin"] / 0.04) * 0.04 - round(s["debut"] / 0.04) * 0.04 for s in segments)
    assert durees["video"] == pytest.approx(attendu, abs=0.041)
    assert abs(durees["video"] - durees["audio"]) <= 0.03, durees
