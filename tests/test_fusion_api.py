"""fusion_api sur une fausse géométrie : reconnaissance des chants, marquage, couleurs, tableau, chants disparus."""
import json
import sys

import pytest

import faux_adsk
import geometrie_fausse as gf


@pytest.fixture
def fa():
    faux_adsk.installer()
    for n in [n for n in sys.modules if n == "edgebanding" or n.startswith("edgebanding.")]:
        del sys.modules[n]
    import adsk  # noqa: F811
    from edgebanding import fusion_api
    fusion_api.vider_cache()
    yield fusion_api, adsk
    faux_adsk.retirer()
    for n in [n for n in sys.modules if n == "edgebanding" or n.startswith("edgebanding.")]:
        del sys.modules[n]


REF = {"cle": "abs2", "nom": "ABS 2 mm blanc", "epaisseur": 2.0, "couleur": "orange"}


def test_reconnaissance_et_mesure(fa):
    api, adsk = fa
    b = gf.panneau(adsk, 720, 560, 19)
    info = api.info_corps(b)
    assert info.axe == (0, 0, 1)
    assert (round(info.longueur, 6), round(info.largeur, 6), round(info.epaisseur, 6)) == (720, 560, 19)
    dessus, dessous, avant, arriere, gauche, droite = b.faces
    assert not api.est_face_chant(dessus) and not api.est_face_chant(dessous)
    assert all(api.est_face_chant(f) for f in (avant, arriere, gauche, droite))
    assert api.longueur_face(avant) == pytest.approx(720) and api.longueur_face(gauche) == pytest.approx(560)
    assert {api.cote_face(f) for f in (avant, arriere)} == {"+v", "-v"}
    assert {api.cote_face(f) for f in (gauche, droite)} == {"+u", "-u"}


def test_marquer_garde_l_identifiant_puis_demarquer(fa):
    api, adsk = fa
    f = gf.panneau(adsk, 600, 300, 19).faces[2]
    d1 = api.marquer(f, REF)
    d2 = api.marquer(f, dict(REF, cle="noir", nom="ABS noir", couleur="violet"))
    assert d1["id"] == d2["id"] and api.lire_marque(f)["reference"] == "ABS noir"
    assert api.lire_marque(f)["couleur"] == "#8E44AD"
    api.demarquer(f)
    assert api.lire_marque(f) is None


def test_colorer_puis_retirer_rend_l_apparence(fa, monkeypatch):
    api, adsk = fa
    b = gf.panneau(adsk, 600, 300, 19)
    design = gf.Design([b])
    f = b.faces[2]
    peinte = gf.Apparence("Edge banding · ABS 2 mm blanc · #FF7A00")
    monkeypatch.setattr(api, "apparence_chant", lambda *a, **k: peinte)
    api.marquer(f, REF)
    assert api.colorer_tout(None, design) == 1
    assert f.appearance is peinte and api.lire_marque(f)["colore"] is True and api.lire_marque(f)["origine"] == ""
    api.colorer(None, design, f)  # deuxième passage : l'origine notée ne change pas
    assert api.lire_marque(f)["origine"] == ""
    assert api.retirer_couleurs(design) == 1
    assert f.appearance is None  # surcharge retirée
    assert "colore" not in api.lire_marque(f) and api.lire_marque(f)["reference"] == "ABS 2 mm blanc"


def test_tableau_et_chants_disparus(fa):
    api, adsk = fa
    b1 = gf.panneau(adsk, 720, 560, 19, "Côté")
    b2 = gf.panneau(adsk, 800, 300, 19, "Étagère", ox=1000)
    design = gf.Design([b1, b2])
    for f in (b1.faces[2], b1.faces[4], b2.faces[3]):
        api.marquer(f, REF)
    reg = api.ecrire_registre(design)
    assert len(reg) == 3 and json.loads(design.attributes.itemByName(api.GROUPE, api.ATTR_REGISTRE).value) == reg
    pieces = api.lire_pieces(design)
    assert [p.nom for p in pieces] == ["Côté", "Étagère"]
    cote = pieces[0]
    assert (cote.longueur, cote.largeur, cote.epaisseur, cote.quantite) == (720, 560, 19, 1)
    assert sorted(c.longueur for c in cote.chants) == [560, 720]
    assert api.chants_disparus(design) == []
    api.demarquer(b2.faces[3])  # la face a disparu (modification de la pièce)
    perdus = api.chants_disparus(design)
    assert len(perdus) == 1 and perdus[0]["piece"] == "Étagère" and perdus[0]["longueur"] == 800


def test_appliquer_du_pinceau(fa, monkeypatch):
    api, adsk = fa
    from edgebanding import contexte, pinceau
    contexte.log = __import__("logging").getLogger("test")
    b = gf.panneau(adsk, 600, 300, 19)
    design = gf.Design([b])
    peinte = gf.Apparence("peinte")
    monkeypatch.setattr(api, "apparence_chant", lambda *a, **k: peinte)
    monkeypatch.setattr(api, "surbrillance_active", lambda d: False)
    biblio = [REF, {"cle": "chene", "nom": "Chêne", "epaisseur": 0.6, "couleur": "vert"}]
    f2, f3 = b.faces[2], b.faces[3]
    k2, k3 = api.cle_face(f2), api.cle_face(f3)
    bilan = pinceau.appliquer(None, design, {k2: "abs2", k3: "chene"}, {k2: [f2], k3: [f3]}, {}, biblio, "couleur")
    assert bilan == {"marques": 2, "retires": 0, "colores": 2, "echecs": 0}
    assert api.lire_marque(f3)["reference"] == "Chêne" and f3.appearance is peinte
    # gomme sur f3, mode « aucune » : f2 garde sa marque mais perd sa couleur
    bilan = pinceau.appliquer(None, design, {k2: "abs2"}, {k2: [f2]}, {k2: f2, k3: f3}, biblio, "aucune")
    assert bilan["retires"] == 1 and api.lire_marque(f3) is None and f3.appearance is None
    assert api.lire_marque(f2) and "colore" not in api.lire_marque(f2) and f2.appearance is None
    assert len(api.lire_registre(design)) == 1
