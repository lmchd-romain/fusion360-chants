"""Noyau pur : reconnaître un chant, le mesurer, totaliser, débit, chants disparus, résumé."""
import math

import pytest

from edgebanding import chants
from edgebanding.chants import ChantLu, FacePlane, PieceLue


class T:
    """Textes minimaux : clé + variables, virgule décimale."""
    langue = "fr"

    def __call__(self, cle, **v):
        return cle + ("(" + ",".join(f"{k}={v[k]}" for k in sorted(v)) + ")" if v else "")

    def nombre(self, x, d=1):
        return f"{x:.{d}f}".replace(".", ",")


def boite(L, W, E):
    return [(x, y, z) for x in (0, L) for y in (0, W) for z in (0, E)]


def test_axe_epaisseur_est_la_normale_de_la_plus_grande_face():
    faces = [FacePlane(600 * 400, (0, 0, 1)), FacePlane(600 * 18, (0, 1, 0)), FacePlane(400 * 18, (1, 0, 0))]
    assert chants.axe_epaisseur(faces) == (0, 0, 1)
    assert chants.axe_epaisseur([]) is None


@pytest.mark.parametrize("genre, direction, attendu", [
    ("plan", (0, 1, 0), True),          # chant long
    ("plan", (1, 0, 0), True),          # bout
    ("plan", (0, 0, 1), False),         # dessus
    ("plan", (0, 0.7071, 0.7071), False),  # chanfrein
    ("cylindre", (0, 0, 1), True),      # chant cintré (axe // épaisseur)
    ("cylindre", (1, 0, 0), False),     # arrondi d'arête
    ("cone", (0, 0, 1), False),
    ("plan", None, False),
])
def test_est_chant(genre, direction, attendu):
    assert chants.est_chant(genre, direction, (0, 0, 1)) is attendu


def test_dimensions_longueur_toujours_la_plus_grande():
    pts = boite(400, 600, 18)
    L, W, E, u, v = chants.dimensions(pts, (0, 0, 1), (1, 0, 0))  # arête la plus longue mal choisie : échange
    assert (round(L, 6), round(W, 6), round(E, 6)) == (600, 400, 18)
    assert abs(chants._dot(u, v)) < 1e-9 and abs(chants._dot(u, (0, 0, 1))) < 1e-9


def test_dimensions_panneau_tourne():
    a = math.radians(30)
    rot = lambda p: (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2])
    pts = [rot(p) for p in boite(800, 300, 19)]
    L, W, E, _, _ = chants.dimensions(pts, (0, 0, 1), rot((1, 0, 0)))
    assert (round(L, 6), round(W, 6), round(E, 6)) == (800, 300, 19)


def test_longueur_chant_droit_et_cintre():
    assert chants.longueur_chant(600 * 18, 18) == 600
    assert chants.longueur_chant(math.pi * 100 / 2 * 18, 18) == pytest.approx(157.08, abs=0.01)
    assert chants.longueur_chant(100, 0) == 0


def test_cote_du_chant():
    centre, u, v = (300, 200, 9), (1, 0, 0), (0, 1, 0)
    assert chants.cote_du_chant((1, 0, 0), (600, 200, 9), centre, u, v) == "+u"
    assert chants.cote_du_chant((-1, 0, 0), (0, 200, 9), centre, u, v) == "-u"
    assert chants.cote_du_chant((0, -1, 0), (300, 400, 9), centre, u, v) == "+v"  # normale inversée : la position tranche
    assert chants.cote_du_chant((0, 1, 0), (300, 0, 9), centre, u, v) == "-v"
    assert chants.cote_du_chant((0.7, 0.7, 0), (500, 380, 9), centre, u, v) is None
    assert chants.cote_du_chant(None, (0, 0, 0), centre, u, v) is None


def test_boites():
    a = ((0, 0, 0), (10, 10, 10))
    assert chants.boites_se_touchent(a, ((10, 0, 0), (20, 10, 10)))
    assert chants.boites_se_touchent(a, ((10.3, 0, 0), (20, 10, 10)))
    assert not chants.boites_se_touchent(a, ((11, 0, 0), (20, 10, 10)))
    assert chants.point_dans_boite((10.02, 5, 5), a) and not chants.point_dans_boite((10.2, 5, 5), a)


def _piece(q=1):
    return PieceLue("Côté", q, 720, 560, 19, [
        ChantLu("a", "ABS 2 mm blanc", 2, "#FF7A00", 720, "+v"),
        ChantLu("b", "ABS 2 mm blanc", 2, "#FF7A00", 560, "+u"),
        ChantLu("c", "ABS 0,8 mm blanc", 0.8, "#FFC400", 720, "-v"),
    ])


def test_debit():
    assert chants.debit(_piece()) == (718, pytest.approx(557.2))
    assert chants.debit(PieceLue("x", 1, 500, 300, 19)) == (500, 300)


def test_totaux_quantite_et_marge():
    tot = chants.totaux([_piece(2), PieceLue("Étagère", 1, 800, 300, 19,
                                              [ChantLu("d", "ABS 2 mm blanc", 2, "#FF7A00", 800, "+v")])], 40)
    abs2 = next(x for x in tot if x.epaisseur == 2)
    assert abs2.nombre == 2 * 2 + 1
    assert abs2.longueur_nette == 2 * (720 + 560) + 800
    assert abs2.longueur_avec_marge == 2 * (720 + 40 + 560 + 40) + 840
    abs08 = next(x for x in tot if x.epaisseur == 0.8)
    assert (abs08.nombre, abs08.longueur_nette) == (2, 1440)
    assert chants.totaux([_piece()], -5)[0].longueur_avec_marge == chants.totaux([_piece()], 0)[0].longueur_nette


def test_chant_par_cote_plusieurs_faces_sur_un_cote():
    p = PieceLue("x", 1, 600, 300, 19, [ChantLu("a", "A", 2, "#000000", 200, "+v"),
                                        ChantLu("b", "A", 2, "#000000", 400, "+v"),
                                        ChantLu("c", "B", 1, "#000000", 157, None)])
    r = chants.chant_par_cote(p)
    assert r["+v"].ident == "b" and {c.ident for c in r["autres"]} == {"a", "c"} and r["-u"] is None


def test_disparus():
    reg = {"a": {"piece": "Côté", "reference": "ABS", "longueur": 720}, "b": {"piece": "Fond", "reference": "ABS",
                                                                              "longueur": 500}}
    assert chants.disparus(reg, {"a"}) == [{"piece": "Fond", "reference": "ABS", "longueur": 500, "ident": "b"}]
    assert chants.disparus({}, {"a"}) == []


def test_resume():
    t = T()
    assert chants.resume([], t) == "resume.vide"
    assert chants.resume([("ABS 2 mm", 1000), ("ABS 2 mm", 2400)], t) == "resume.une(m=3,40,n=2,ref=ABS 2 mm)"
    r = chants.resume([("ABS 2 mm", 1000), ("Chêne", 500)], t).split("\n")
    assert r[0] == "resume.total(m=1,50,n=2)" and len(r) == 3
