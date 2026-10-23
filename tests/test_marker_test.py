"""Test des marqueurs : fusion des événements, détection des trous, sorties."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

import marker_test
from marker_test import analyser, fusionner, raccords_de_cutlist


def ev(*temps, canal="texte"):
    return [{"t": t, "canal": canal, "label": f"e{t}"} for t in temps]


def test_fusion_dans_la_fenetre():
    assert len(fusionner(ev(1.0, 1.2, 1.35), 0.4)) == 1
    assert len(fusionner(ev(1.0, 1.5), 0.4)) == 2
    # la fenêtre part du premier événement de la grappe, pas du précédent : pas d'effet de chaîne
    assert [i["t"] for i in fusionner(ev(1.0, 1.3, 1.6, 1.9), 0.4)] == [1.0, 1.6]
    # des canaux différents au même instant = une seule information
    assert len(fusionner(ev(2.0) + ev(2.1, canal="sfx"), 0.4)) == 1


def test_trous_et_bornes():
    r = analyser(ev(2, 4, 10, 12, 18), 20.0, fusion=0.4, trou=4.0)
    assert [(t["debut"], t["fin"]) for t in r["trous"]] == [(4, 10), (12, 18)]
    assert r["intervalle_median"] == 2.0
    assert r["plus_grand_ecart"] == 6.0
    assert r["informations"] == 5


def test_trou_au_debut_et_a_la_fin():
    r = analyser(ev(5.0, 7.0), 12.0)
    assert [(t["debut"], t["fin"]) for t in r["trous"]] == [(0.0, 5.0), (7.0, 12.0)]
    assert r["trous"][1]["apres"] == "fin de la vidéo"


def test_pile_au_seuil_n_est_pas_un_trou():
    r = analyser(ev(4.0, 8.0), 12.0, trou=4.0)
    assert r["trous"] == []


def test_fusion_ne_cache_pas_un_trou():
    # 0,3 s après 4 s : fusionné, l'information suivante est à 9 s → trou de 5 s
    r = analyser(ev(1, 4.0, 4.3, 9.0), 10.0)
    assert [(t["debut"], t["fin"]) for t in r["trous"]] == [(4.0, 9.0)]


def test_raccords_de_la_cutlist_sur_la_timeline_montee():
    cl = {"segments": [{"debut": 0, "fin": 2}, {"debut": 3, "fin": 5}, {"debut": 7, "fin": 8}]}
    r = raccords_de_cutlist(cl)
    assert [e["t"] for e in r] == [2.0, 4.0]
    assert all(e["canal"] == "image" for e in r)


def test_evenements_hors_video_ignores():
    r = analyser(ev(-1, 3, 50), 6.0)
    assert r["evenements_hors_video"] == 2
    assert r["evenements"] == 1


def test_cli_code_de_sortie_et_fichiers(tmp_path):
    (tmp_path / "ev.json").write_text(json.dumps(ev(1, 3, 5, 7, 9.5)))
    (tmp_path / "cut.json").write_text(json.dumps({"segments": [{"debut": 0, "fin": 6}, {"debut": 8, "fin": 13}],
                                                   "duree_apres": 11.0}))
    sortie = tmp_path / "rythme"
    assert marker_test.main(["--evenements", str(tmp_path / "ev.json"), "--cutlist", str(tmp_path / "cut.json"),
                             "--sortie", str(sortie)]) == 0
    r = json.loads((sortie / "marker_test.json").read_text())
    assert r["duree"] == 11.0 and r["trous"] == []
    racine = ET.parse(sortie / "timeline.svg").getroot()           # SVG bien formé
    assert racine.tag.endswith("svg")
    assert "TROUS" in (sortie / "rapport.txt").read_text()

    (tmp_path / "ev2.json").write_text(json.dumps({"evenements": ev(1, 2)}))
    assert marker_test.main(["--duree", "10", "--evenements", str(tmp_path / "ev2.json"),
                             "--sortie", str(sortie)]) == 1
    r = json.loads((sortie / "marker_test.json").read_text())
    assert [(t["debut"], t["fin"]) for t in r["trous"]] == [(2.0, 10.0)]
    svg = (sortie / "timeline.svg").read_text()
    assert 'fill="#ff3b30"' in svg                                   # le trou est surligné
    ET.fromstring(svg)


def test_cli_sans_duree_ni_cutlist(tmp_path, capsys):
    (tmp_path / "ev.json").write_text("[]")
    with pytest.raises(SystemExit) as e:
        from commun import executer
        executer(lambda: marker_test.main(["--evenements", str(tmp_path / "ev.json"), "--sortie", str(tmp_path)]))
    assert e.value.code == 2
