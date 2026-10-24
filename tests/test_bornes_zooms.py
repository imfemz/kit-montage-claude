"""Bornes à l'énergie (recalage des débuts de Whisper), vérification d'une coupe à l'oreille, zooms au début des phrases qui tournent."""

from __future__ import annotations

import numpy as np

from conftest import voix_synthetique

import verifier_coupe
import zooms
from derush import Grille, planifier, recaler_debuts, rms_par_fenetre, verifier_coupes

SR = 16000


def _mots(intervalles, noms=None):
    return [{"mot": (noms[i] if noms else f"m{i}"), "debut": d, "fin": f, "proba": 1.0} for i, (d, f) in enumerate(intervalles)]


# ------------------------------------------------------------------ recalage sur l'énergie

def test_debut_avance_jusqu_a_l_attaque_reelle():
    """Whisper fait commencer le 2e mot à 1,5 s alors que la voix part à 2,0 s : on le recale à 2,0 s."""
    reel = [(0.3, 0.9), (2.0, 2.6)]
    x = voix_synthetique(3.2, reel, sr=SR, bruit=0.0005)
    db = rms_par_fenetre(x.astype(np.float32), SR)
    whisper = _mots([(0.3, 0.9), (1.5, 2.6)])
    mots, n = recaler_debuts(whisper, db)
    assert n == 1
    assert abs(mots[1]["debut"] - 2.0) <= 0.03, mots[1]
    assert mots[1]["debut_whisper"] == 1.5
    assert mots[0]["debut"] == 0.3            # un mot qui commence déjà dans la voix ne bouge pas


def test_le_blanc_retire_va_jusqu_a_la_vraie_voix():
    """Avec le recalage, la coupe de sortie du blanc tombe près de l'attaque réelle, pas dans le silence de Whisper."""
    reel = [(0.3, 0.9), (2.4, 3.0)]
    x = voix_synthetique(3.5, reel, sr=SR, bruit=0.0005)
    db = rms_par_fenetre(x.astype(np.float32), SR)
    whisper = _mots([(0.3, 0.9), (1.9, 3.0)])
    mots, _ = recaler_debuts(whisper, db)
    segments, raccourcis, _ = planifier(mots, 3.5, db, Grille(), 1.0, 0.25, 0.040)
    c2 = [r for r in raccourcis if r["sorte"] == "milieu"][0]["coupe"][1]
    assert 2.0 < c2 <= 2.4 - 0.040, c2       # sans recalage, elle serait avant 1,9 s
    assert verifier_coupes(segments, mots, 0.040, 3.5) == []


def test_pas_d_attaque_pas_de_recalage():
    """Un « mot » sans voix dessous (hallucination) garde l'heure de Whisper : en cas de doute, on ne touche à rien."""
    x = voix_synthetique(3.0, [(0.3, 0.9)], sr=SR, bruit=0.0005)
    db = rms_par_fenetre(x.astype(np.float32), SR)
    mots, n = recaler_debuts(_mots([(0.3, 0.9), (1.8, 2.4)]), db)
    assert n == 0 and mots[1]["debut"] == 1.8


# ------------------------------------------------------------------ vérifier une coupe à l'oreille

FREQ = {"et": 200, "donc": 400, "jai": 600}


def _voix_et_donc():
    """« et » (200 Hz) 1,00-1,15 · creux · « donc » (400 Hz) 1,22-1,50 · « j'ai » (600 Hz) 1,55-1,80."""
    n = int(2.4 * SR); t = np.arange(n) / SR
    x = 0.0005 * np.random.default_rng(3).standard_normal(n)
    for (d, f), hz in (((1.00, 1.15), 200), ((1.22, 1.50), 400), ((1.55, 1.80), 600)):
        i0, i1 = int(d * SR), int(f * SR)
        x[i0:i1] += 0.3 * np.sin(np.pi * (t[i0:i1] - d) / (f - d)) ** 0.3 * np.sin(2 * np.pi * hz * t[i0:i1])
    return x.astype(np.float32)


def _faux_whisper(audio, sr):
    """Reconnaît chaque « mot » à sa fréquence : le texte entendu, dans l'ordre."""
    n = int(0.02 * sr); env = np.sqrt(np.convolve(audio ** 2, np.ones(n) / n, mode="same"))
    fort = env > env.max() * 0.1
    texte, i = [], 0
    while i < len(audio):
        if fort[i]:
            j = i
            while j < len(audio) and fort[j]:
                j += 1
            seg = audio[i:j]
            if len(seg) > n:
                hz = np.fft.rfftfreq(len(seg), 1 / sr)[np.argmax(np.abs(np.fft.rfft(seg)))]
                texte.append(min(FREQ, key=lambda m: abs(FREQ[m] - hz)))
            i = j
        i += 1
    return " ".join("j'ai" if m == "jai" else m for m in texte)


def test_premier_mot_entendu():
    x = _voix_et_donc()
    assert verifier_coupe.premier_mot(x, SR, 0.95, _faux_whisper) == "et"       # coupe trop tôt : on entend encore « et »
    assert verifier_coupe.premier_mot(x, SR, 1.18, _faux_whisper) == "donc"     # coupe dans le creux : propre


def test_chercher_le_premier_creux_qui_passe():
    x = _voix_et_donc()
    t, essais = verifier_coupe.chercher(x, SR, rms_par_fenetre(x, SR), 1.00, "Donc", _faux_whisper)
    assert t is not None and 1.15 <= t <= 1.22, (t, essais)


def test_coupe_impossible():
    x = _voix_et_donc()
    t, _ = verifier_coupe.chercher(x, SR, rms_par_fenetre(x, SR), 1.00, "alors", _faux_whisper)
    assert t is None


# ------------------------------------------------------------------ zooms

def _phrase(t, texte, debit=0.25):
    return [{"mot": w, "debut": round(t + i * debit, 3), "fin": round(t + i * debit + 0.2, 3)} for i, w in enumerate(texte.split())]


def test_roles():
    assert zooms.role("Mais personne ne le voit.", 3) == "contraste"
    assert zooms.role("Du coup ça change tout.", 3) == "consequence"
    assert zooms.role("Par exemple ce plan-là.", 3) == "exemple"
    assert zooms.role("Le rythme, c'est la diversité des infos.", 3) == "definition"
    assert zooms.role("Ça c'est vraiment bien.", 3) == "explication"
    assert zooms.role("Il sert à quoi, le monteur ?", 3) == "question"
    assert zooms.role("J'ai monté cette vidéo.", 0) == "accroche"


def test_planifier_regles_des_zooms():
    mots = (_phrase(0, "Si une IA peut monter cette vidéo.") + _phrase(4, "Mais ça ne suffit pas.")
            + _phrase(10, "Donc j'ai tout noté.") + _phrase(12, "Le carnet, c'est trois lignes.")
            + _phrase(25, "Je les relis à chaque fois.") + _phrase(41, "Je les relis encore une fois.")
            + _phrase(45, "Par exemple ce zoom.") + _phrase(49, "Fin de la vidéo."))
    z = zooms.planifier(zooms.phrases(mots), coupes=[20.0], fin_video=51.0)
    assert [(x["t"], x["role"]) for x in z] == [(0, "accroche"), (10, "consequence"), (41, "relance")]
    assert [(x["de"], x["a"]) for x in z] == [(1.0, 1.085), (1.085, 1.0), (1.0, 1.085)]     # avant, arrière, avant
    assert all(x["duree"] == 0.85 for x in z)


def test_remappage_sur_la_video_montee():
    mots = _phrase(10, "Mais regarde bien.")
    segs = [{"debut": 0.0, "fin": 2.0}, {"debut": 9.5, "fin": 12.0}]
    out = zooms.remapper(mots, segs)
    assert out[0]["debut"] == 2.5 and zooms.coupes_montage(segs) == [2.0]
