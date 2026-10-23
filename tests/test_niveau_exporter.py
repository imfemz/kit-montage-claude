"""Mesure EBU R128 et export normalisé, sur des signaux synthétiques."""

from __future__ import annotations

import numpy as np
import pytest

from conftest import creer_video, ecrire_wav, ffmpeg_requis

import exporter
from niveau import mesurer, sonie_integree

SR = 48000
pytestmark = ffmpeg_requis


def sinus(duree, amp, f=1000.0):
    t = np.arange(int(duree * SR)) / SR
    return amp * np.sin(2 * np.pi * f * t)


def parole_synthetique(duree, niveau_rms, graine=0):
    """Bruit rose approximatif modulé en syllabes et en phrases, avec des pauses : crête ≈ 12 dB."""
    rng = np.random.default_rng(graine)
    n = int(duree * SR)
    blanc = rng.standard_normal(n)
    spectre = np.fft.rfft(blanc)
    f = np.fft.rfftfreq(n, 1 / SR)
    spectre[1:] /= np.sqrt(f[1:] / 100.0)
    spectre[f < 80] = 0
    rose = np.fft.irfft(spectre, n)
    t = np.arange(n) / SR
    syllabes = (0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)) ** 2
    phrases = (np.sin(2 * np.pi * t / 6.0) > -0.6).astype(float)
    x = rose * syllabes * phrases
    return x * (niveau_rms / np.sqrt(np.mean(x ** 2)))


def test_sinus_1khz_mesure_attendue(tmp_path):
    # sinus de crête −20 dBFS en mono : −23,0 LUFS (BS.1770), true peak −20 dBTP
    wav = ecrire_wav(tmp_path / "s.wav", sinus(12, 0.1), SR)
    m = mesurer(wav)
    assert m["integree_lufs"] == pytest.approx(-23.0, abs=0.2)
    assert m["true_peak_dbtp"] == pytest.approx(-20.0, abs=0.2)
    assert m["variations"] == []


def test_variation_detectee_par_fenetre(tmp_path):
    x = np.concatenate([sinus(10, 0.1), sinus(10, 0.1), sinus(10, 0.02)])   # dernière fenêtre −14 dB
    m = mesurer(ecrire_wav(tmp_path / "v.wav", x, SR))
    assert len(m["fenetres"]) == 3
    assert m["fenetres"][0]["lufs"] == pytest.approx(-23.0, abs=0.3)
    assert m["fenetres"][2]["lufs"] == pytest.approx(-37.0, abs=0.5)
    assert [f["debut"] for f in m["variations"]] == [20.0]
    assert m["variations"][0]["etat"] == "variation"


def test_fenetre_silencieuse_signalee(tmp_path):
    x = np.concatenate([sinus(10, 0.1), np.zeros(10 * SR), sinus(10, 0.1)])
    m = mesurer(ecrire_wav(tmp_path / "s.wav", x, SR))
    assert [f["etat"] for f in m["fenetres"]] == ["ok", "silence", "ok"]


def test_sonie_integree_porte_relative():
    # un bloc à −20 et un bloc à −40 : le second est sous la porte relative (−20 − 3 − 10)
    assert sonie_integree([-20.0, -40.0]) == pytest.approx(-20.0, abs=0.01)
    assert sonie_integree([-80.0]) == float("-inf")


@pytest.mark.parametrize("cas, methode", [
    ("sinus_module", "loudnorm linéaire"),        # ≈ −30 LUFS, crêtes basses : loudnorm reste linéaire
    ("parole", "gain + limiteur"),                # ≈ −30 LUFS, crêtes hautes : le gain seul dépasserait −1 dBTP
    ("sinus_constant", "gain + limiteur"),        # LRA nulle : loudnorm refuse le mode linéaire
])
def test_export_normalise_a_0_5_lu(tmp_path, capsys, cas, methode):
    if cas == "sinus_module":
        x = np.concatenate([sinus(3, a, f=440) for a in (0.05, 0.03, 0.05, 0.02, 0.05)])
    elif cas == "parole":
        x = parole_synthetique(14, 10 ** (-32 / 20))
    else:
        x = sinus(14, 0.05, f=440)
    video = creer_video(tmp_path / "in.mp4", ecrire_wav(tmp_path / "in.wav", x, SR))
    sortie = tmp_path / "final.mp4"
    code = exporter.main([str(video), "--sortie", str(sortie), "--preset", "ultrafast"])
    assert methode in capsys.readouterr().out
    m = mesurer(sortie)                                # re-mesure indépendante du fichier livré
    assert abs(m["integree_lufs"] - (-14.0)) <= 0.5, m
    assert m["true_peak_dbtp"] <= -1.0 + 0.05, m
    # second instrument : le compteur interne de loudnorm doit confirmer la mesure d'ebur128
    autre = exporter.mesure_loudnorm(sortie, -14, -1, 11)
    assert abs(float(autre["input_i"]) - (-14.0)) <= 0.5, autre
    assert float(autre["input_tp"]) <= -1.0 + 0.1, autre
    assert code == 0
