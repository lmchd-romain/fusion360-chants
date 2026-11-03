"""Logique du pinceau (sans Fusion) : un clic plaque, un nouveau clic retire, les occurrences suivent."""
import sys

import pytest

import faux_adsk


class Face:
    def __init__(self, k, occ=0, chant=True):
        self.k, self.occ, self.chant = k, occ, chant

    def __repr__(self):
        return f"{self.k}@{self.occ}"


class Selection:
    def __init__(self):
        self.liste = []

    @property
    def selectionCount(self):
        return len(self.liste)

    def selection(self, i):
        return type("S", (), {"entity": self.liste[i]})()

    def clearSelection(self):
        self.liste = []

    def addSelection(self, e):
        self.liste.append(e)
        return True

    def clic(self, e):  # comportement de Fusion : un clic bascule l'entité
        if e in self.liste:
            self.liste.remove(e)
        else:
            self.liste.append(e)


@pytest.fixture
def p(monkeypatch):
    faux_adsk.installer()
    for n in [n for n in sys.modules if n == "edgebanding" or n.startswith("edgebanding.")]:
        del sys.modules[n]
    import adsk
    from edgebanding import fusion_api, pinceau
    monkeypatch.setattr(adsk.fusion.BRepFace, "cast", staticmethod(lambda e: e))
    portes = {"porte": [Face("porte", 0), Face("porte", 1)]}
    monkeypatch.setattr(fusion_api, "cle_face", lambda f: f.k)
    monkeypatch.setattr(fusion_api, "natif", lambda f: f)
    monkeypatch.setattr(fusion_api, "est_face_chant", lambda f: f.chant)
    monkeypatch.setattr(fusion_api, "proxys", lambda d, f: portes.get(f.k, [f]))
    sel = Selection()
    pinceau._etat.clear()
    pinceau._etat.update({"design": None, "biblio": [{"cle": "a", "nom": "A", "epaisseur": 2, "couleur": "orange"}],
                          "ref": "a", "marques": {}, "entites": {}, "initiales": {}, "longueurs": {},
                          "champs": {"chants": sel}, "message": ""})
    yield pinceau, sel, portes
    faux_adsk.retirer()


def test_clic_plaque_puis_gomme(p):
    pinceau, sel, _ = p
    f = Face("f1")
    sel.clic(f)
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {"f1": "a"}
    sel.clic(f)
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {} and sel.liste == []


def test_face_refusee_retiree_de_la_selection(p):
    pinceau, sel, _ = p
    sel.clic(Face("dessus", chant=False))
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {} and sel.liste == []


def test_composant_deux_fois_les_occurrences_suivent(p):
    pinceau, sel, portes = p
    sel.clic(portes["porte"][0])
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {"porte": "a"} and len(sel.liste) == 2  # l'autre porte s'allume aussi
    pinceau._etat["ref"] = "b"
    sel.clic(sel.liste[1])  # gomme sur la seconde porte
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {} and sel.liste == []


def test_reference_courante_au_moment_du_clic(p):
    pinceau, sel, _ = p
    sel.clic(Face("f1"))
    pinceau._selection_changee()
    pinceau._etat["ref"] = "b"
    sel.clic(Face("f2"))
    pinceau._selection_changee()
    assert pinceau._etat["marques"] == {"f1": "a", "f2": "b"}
