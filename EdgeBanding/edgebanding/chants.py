"""Noyau pur des chants : reconnaître un chant, le mesurer, le ranger par côté, totaliser, débit, chants disparus.

Aucun import adsk. Unités : mm. Vecteurs : tuples (x, y, z).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

TOL_PARALLELE = 0.02   # |cos| : face de chant si sa normale est perpendiculaire à l'axe d'épaisseur à 1,1° près
COTES = ("+u", "-u", "+v", "-v")  # +v / -v = côtés longs, +u / -u = côtés courts (bouts)


# --- vecteurs ---------------------------------------------------------------------------------------------------

def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _croix(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norme(a):
    n = math.sqrt(_dot(a, a))
    if n < 1e-12:
        raise ValueError("vecteur nul")
    return (a[0] / n, a[1] / n, a[2] / n)


def _moins(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


# --- reconnaître un panneau et ses chants -----------------------------------------------------------------------

@dataclass(frozen=True)
class FacePlane:
    aire: float              # mm²
    normale: tuple


def axe_epaisseur(faces_planes: list[FacePlane]) -> tuple | None:
    """Normale de la plus grande face plane : l'axe d'épaisseur du panneau. None si aucune face plane."""
    if not faces_planes:
        return None
    return _norme(max(faces_planes, key=lambda f: f.aire).normale)


def etendue(points, axe) -> float:
    """Longueur de la projection des points sur l'axe."""
    v = [_dot(p, axe) for p in points]
    return (max(v) - min(v)) if v else 0.0


def est_chant(genre: str, direction, axe) -> bool:
    """genre « plan » : direction = normale ; « cylindre » : direction = axe du cylindre.

    Plan : chant si la normale est perpendiculaire à l'axe d'épaisseur. Cylindre : chant courbe si son axe est
    parallèle à l'axe d'épaisseur. Toute autre face (dessus, dessous, chanfrein, cône…) n'est pas un chant.
    """
    if axe is None or direction is None:
        return False
    c = abs(_dot(_norme(direction), axe))
    if genre == "plan":
        return c < TOL_PARALLELE
    if genre == "cylindre":
        return c > 1 - TOL_PARALLELE
    return False


def axes_plan(axe, direction_longue):
    """Repère du panneau : u le long de direction_longue (projetée dans le plan), v = axe × u."""
    d = _moins(direction_longue, tuple(_dot(direction_longue, axe) * c for c in axe))
    u = _norme(d)
    v = _norme(_croix(axe, u))
    return u, v


def dimensions(points, axe, direction_longue):
    """(longueur, largeur, épaisseur, u, v) du panneau ; longueur ≥ largeur (u et v échangés au besoin)."""
    u, v = axes_plan(axe, direction_longue)
    L, W = etendue(points, u), etendue(points, v)
    if W > L:
        u, v, L, W = v, tuple(-c for c in u), W, L
    return L, W, etendue(points, axe), u, v


def longueur_chant(aire_mm2: float, epaisseur_mm: float) -> float:
    """Longueur d'un chant = aire de sa face / épaisseur du panneau (exact pour un chant droit ou cintré)."""
    if epaisseur_mm <= 0:
        return 0.0
    return aire_mm2 / epaisseur_mm


def cote_du_chant(normale, point, centre, u, v) -> str | None:
    """Côté du rectangle de la pièce : « +u », « -u » (bouts), « +v », « -v » (côtés longs) ; None si oblique/courbe."""
    if normale is None:
        return None
    n = _norme(normale)
    d = _moins(point, centre)
    if abs(_dot(n, u)) > 0.9:
        return "+u" if _dot(d, u) > 0 else "-u"
    if abs(_dot(n, v)) > 0.9:
        return "+v" if _dot(d, v) > 0 else "-v"
    return None


# --- boîtes englobantes (pré-tri du test de contact) ------------------------------------------------------------

def boites_se_touchent(a, b, jeu: float = 0.5) -> bool:
    """a, b : ((xmin, ymin, zmin), (xmax, ymax, zmax)) en mm ; vrai si elles se touchent à `jeu` près."""
    return all(a[0][i] - jeu <= b[1][i] and b[0][i] - jeu <= a[1][i] for i in range(3))


def point_dans_boite(p, b, jeu: float = 0.05) -> bool:
    return all(b[0][i] - jeu <= p[i] <= b[1][i] + jeu for i in range(3))


# --- tableau des chants -----------------------------------------------------------------------------------------

@dataclass
class ChantLu:
    ident: str
    reference: str           # nom de la référence, tel qu'écrit sur la face
    epaisseur: float         # mm, épaisseur du chant
    couleur: str             # "#RRGGBB"
    longueur: float          # mm
    cote: str | None         # "+u" "-u" "+v" "-v" ou None


@dataclass
class PieceLue:
    nom: str
    quantite: int
    longueur: float          # mm, cote finie
    largeur: float
    epaisseur: float
    chants: list[ChantLu] = field(default_factory=list)


@dataclass
class Total:
    reference: str
    epaisseur: float
    couleur: str
    nombre: int = 0
    longueur_nette: float = 0.0       # mm
    longueur_avec_marge: float = 0.0  # mm


def debit(piece: PieceLue) -> tuple[float, float]:
    """Cote de débit = cote finie − épaisseur des chants des deux bouts (longueur) et des deux côtés longs (largeur)."""
    ep = {c: 0.0 for c in COTES}
    for ch in piece.chants:
        if ch.cote in ep:
            ep[ch.cote] = max(ep[ch.cote], ch.epaisseur)
    return piece.longueur - ep["+u"] - ep["-u"], piece.largeur - ep["+v"] - ep["-v"]


def chant_par_cote(piece: PieceLue) -> dict:
    """{côté: ChantLu} pour les quatre côtés (le plus long s'il y en a plusieurs), plus « autres » : chants hors côtés."""
    r = {c: None for c in COTES}
    autres = []
    for ch in piece.chants:
        if ch.cote in r:
            if r[ch.cote] is None or ch.longueur > r[ch.cote].longueur:
                if r[ch.cote] is not None:
                    autres.append(r[ch.cote])
                r[ch.cote] = ch
            else:
                autres.append(ch)
        else:
            autres.append(ch)
    r["autres"] = autres
    return r


def totaux(pieces: list[PieceLue], marge: float) -> list[Total]:
    """Totaux par référence (nom + épaisseur) ; chaque chant compte `quantite` fois ; marge ajoutée à chaque chant."""
    par = {}
    for p in pieces:
        for ch in p.chants:
            cle = (ch.reference, round(ch.epaisseur, 3))
            t = par.get(cle)
            if t is None:
                t = par[cle] = Total(ch.reference, ch.epaisseur, ch.couleur)
            t.nombre += p.quantite
            t.longueur_nette += ch.longueur * p.quantite
            t.longueur_avec_marge += (ch.longueur + max(marge, 0.0)) * p.quantite
    return sorted(par.values(), key=lambda t: (t.reference.lower(), t.epaisseur))


def disparus(registre: dict, trouves: set) -> list[dict]:
    """Chants inscrits au registre du document mais plus retrouvés sur aucune face."""
    return [dict(v, ident=k) for k, v in sorted(registre.items()) if k not in trouves]


# --- résumé du pinceau ------------------------------------------------------------------------------------------

def resume(chants: list[tuple[str, float]], t) -> str:
    """chants : [(nom de référence, longueur mm)] → « 6 chants · ABS 2 mm · 3,4 m » ou une ligne par référence."""
    if not chants:
        return t("resume.vide")
    par = {}
    for nom, L in chants:
        n, s = par.get(nom, (0, 0.0))
        par[nom] = (n + 1, s + L)
    total = sum(L for _, L in chants)
    if len(par) == 1:
        nom = next(iter(par))
        return t("resume.une", n=len(chants), ref=nom, m=t.nombre(total / 1000, 2))
    lignes = [t("resume.total", n=len(chants), m=t.nombre(total / 1000, 2))]
    for nom, (n, s) in sorted(par.items()):
        lignes.append(t("resume.ligne", n=n, ref=nom, m=t.nombre(s / 1000, 2)))
    return "\n".join(lignes)
