"""Couche Fusion : reconnaître les chants, les marquer (attributs), les colorer, les surligner, les relire pour le tableau.

Seul lieu des conversions cm ↔ mm et des passages proxy ↔ natif. Aucune API preview.
Tout ce qui touche Fusion est [supposé] tant que la recette (essai/recette) ne l'a pas prouvé.
"""
from __future__ import annotations

import json
import uuid

import adsk.core
import adsk.fusion

from . import chants, reglages

GROUPE = "lmchdEdgeBanding"
ATTR_CHANT = "chant"
ATTR_REGISTRE = "registre"
ID_SURBRILLANCE = "lmchdEdgeBandingSurbrillance"
PREFIXE_APPARENCE = "Edge banding"
MM = 10.0      # cm → mm
MM2 = 100.0    # cm² → mm²


class ErreurChants(Exception):
    """Erreur métier : clé de texte + variables, traduite par l'interface."""

    def __init__(self, cle: str, **variables):
        super().__init__(cle)
        self.cle = cle
        self.variables = variables


# --- identité des faces -----------------------------------------------------------------------------------------

def natif(entite):
    try:
        return entite.nativeObject if entite.assemblyContext else entite
    except Exception:  # noqa: BLE001
        return entite


def _jeton(entite) -> str:
    try:
        return entite.entityToken
    except Exception:  # noqa: BLE001 — jeton refusé sur certains objets
        return f"{getattr(entite, 'name', '?')}"


def cle_corps(corps) -> str:
    return _jeton(natif(corps))


def cle_face(face) -> str:
    """Clé de la face NATIVE : deux occurrences d'un même composant partagent leurs chants."""
    f = natif(face)
    return f"{cle_corps(f.body)}#{f.tempId}"


def _mm(p):
    return (p.x * MM, p.y * MM, p.z * MM)


# --- reconnaître un panneau et ses chants -----------------------------------------------------------------------

class InfoCorps:
    """Axe d'épaisseur, épaisseur, repère u/v, centre et boîte (mm) d'un corps, dans le repère de l'entité lue."""

    def __init__(self, corps):
        planes = []
        for f in corps.faces:
            g = f.geometry
            if g.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                n = g.normal
                planes.append((f, chants.FacePlane(f.area * MM2, (n.x, n.y, n.z))))
        self.axe = chants.axe_epaisseur([p for _, p in planes])
        pts = [_mm(v.geometry) for v in corps.vertices]
        if not pts:
            bb = corps.boundingBox
            pts = [_mm(bb.minPoint), _mm(bb.maxPoint)]
        self.points = pts
        b = corps.boundingBox
        self.boite = (_mm(b.minPoint), _mm(b.maxPoint))
        self.centre = tuple((self.boite[0][i] + self.boite[1][i]) / 2 for i in range(3))
        self.epaisseur = chants.etendue(pts, self.axe) if self.axe else 0.0
        self.u = self.v = None
        self.longueur = self.largeur = 0.0
        if self.axe:
            grande = max(planes, key=lambda p: p[1].aire)[0]
            direction = None
            longueur = -1.0
            for e in grande.edges:
                g = e.geometry
                if isinstance(g, adsk.core.Line3D):
                    d = g.startPoint.vectorTo(g.endPoint)
                    if d.length > longueur:
                        longueur, direction = d.length, (d.x, d.y, d.z)
            if direction is None:  # disque, ovale : prendre un axe du plan
                a = self.axe
                direction = (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0)
            self.longueur, self.largeur, _, self.u, self.v = chants.dimensions(pts, self.axe, direction)
            self.centre = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


_cache_info: dict = {}


def vider_cache():
    _cache_info.clear()


def info_corps(corps) -> InfoCorps:
    """Mise en cache par corps (proxy compris : la clé garde le chemin d'occurrence)."""
    try:
        chemin = corps.assemblyContext.fullPathName if corps.assemblyContext else ""
    except Exception:  # noqa: BLE001
        chemin = ""
    cle = f"{chemin}|{cle_corps(corps)}"
    i = _cache_info.get(cle)
    if i is None:
        i = _cache_info[cle] = InfoCorps(corps)
    return i


def _genre_direction(face):
    g = face.geometry
    st = g.surfaceType
    if st == adsk.core.SurfaceTypes.PlaneSurfaceType:
        n = g.normal
        return "plan", (n.x, n.y, n.z)
    if st == adsk.core.SurfaceTypes.CylinderSurfaceType:
        a = g.axis
        return "cylindre", (a.x, a.y, a.z)
    return "autre", None


def est_face_chant(face) -> bool:
    try:
        corps = face.body
        if corps is None or not corps.isSolid:
            return False
        genre, d = _genre_direction(face)
        return chants.est_chant(genre, d, info_corps(corps).axe)
    except Exception:  # noqa: BLE001
        return False


def longueur_face(face) -> float:
    return chants.longueur_chant(face.area * MM2, info_corps(face.body).epaisseur)


def cote_face(face) -> str | None:
    info = info_corps(face.body)
    genre, d = _genre_direction(face)
    if genre != "plan" or info.u is None:
        return None
    return chants.cote_du_chant(d, _mm(face.pointOnFace), info.centre, info.u, info.v)


def nom_piece(corps) -> str:
    comp = corps.parentComponent
    try:
        racine = comp.parentDesign.rootComponent
    except Exception:  # noqa: BLE001
        racine = None
    if comp is None or (racine is not None and comp == racine):
        return corps.name
    if comp.bRepBodies.count > 1:
        return f"{comp.name} / {corps.name}"
    return comp.name


# --- marquage (attributs) ---------------------------------------------------------------------------------------

def lire_marque(face) -> dict | None:
    a = natif(face).attributes.itemByName(GROUPE, ATTR_CHANT)
    if not a:
        return None
    try:
        d = json.loads(a.value)
        return d if isinstance(d, dict) else None
    except (ValueError, TypeError):
        return None


def marquer(face, ref: dict) -> dict:
    """Pose (ou met à jour) l'attribut du chant ; garde l'identifiant et l'apparence d'origine déjà notés."""
    ancien = lire_marque(face) or {}
    d = {"id": ancien.get("id") or uuid.uuid4().hex[:12],
         "cle": ref["cle"], "reference": ref["nom"], "epaisseur": float(ref["epaisseur"]),
         "couleur": reglages.hexa(ref["couleur"])}
    for k in ("origine", "colore"):
        if k in ancien:
            d[k] = ancien[k]
    a = natif(face).attributes.add(GROUPE, ATTR_CHANT, json.dumps(d, ensure_ascii=False))
    if a is None:
        raise ErreurChants("erreur.marquage")
    return d


def demarquer(face) -> None:
    a = natif(face).attributes.itemByName(GROUPE, ATTR_CHANT)
    if a:
        a.deleteMe()


def _ecrire_marque(face, d: dict) -> None:
    natif(face).attributes.add(GROUPE, ATTR_CHANT, json.dumps(d, ensure_ascii=False))


def faces_marquees(design):
    """[(face native, marque)] de tout le document."""
    r = []
    for a in design.findAttributes(GROUPE, ATTR_CHANT):
        f = adsk.fusion.BRepFace.cast(a.parent)
        if f is None:
            continue
        try:
            d = json.loads(a.value)
        except (ValueError, TypeError):
            continue
        if isinstance(d, dict):
            r.append((f, d))
    return r


def proxys(design, face_native):
    """Toutes les apparitions de la face dans l'assemblage (une par occurrence du composant)."""
    racine = design.rootComponent
    comp = face_native.body.parentComponent
    if comp == racine:
        return [face_native]
    occs = racine.allOccurrencesByComponent(comp)
    return [face_native.createForAssemblyContext(o) for o in occs] or [face_native]


# --- registre du document (chants disparus) ---------------------------------------------------------------------

def lire_registre(design) -> dict:
    a = design.attributes.itemByName(GROUPE, ATTR_REGISTRE)
    if not a:
        return {}
    try:
        d = json.loads(a.value)
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


def ecrire_registre(design) -> dict:
    reg = {}
    for f, d in faces_marquees(design):
        if d.get("id"):
            try:
                L = longueur_face(f)
                piece = nom_piece(f.body)
            except Exception:  # noqa: BLE001
                L, piece = 0.0, "?"
            reg[d["id"]] = {"piece": piece, "reference": d.get("reference", ""), "longueur": round(L, 1)}
    design.attributes.add(GROUPE, ATTR_REGISTRE, json.dumps(reg, ensure_ascii=False))
    return reg


def chants_disparus(design) -> list[dict]:
    trouves = {d.get("id") for _, d in faces_marquees(design)}
    return chants.disparus(lire_registre(design), trouves)


# --- apparences (couleur réelle sur la face) --------------------------------------------------------------------

def _propriete_couleur(apparence):
    """Propriété de couleur principale, sans texture branchée ; None si l'apparence n'en a pas."""
    trouve = None
    for i in range(apparence.appearanceProperties.count):
        p = adsk.core.ColorProperty.cast(apparence.appearanceProperties.item(i))
        if p is None:
            continue
        try:
            if p.connectedTexture:
                continue
        except Exception:  # noqa: BLE001
            pass
        if p.id in ("generic_diffuse", "opaque_albedo", "surface_albedo"):
            return p
        trouve = trouve or p
    return trouve


def _source_apparence(app, design):
    """Une apparence unie à copier : d'abord une peinture ou un plastique de la bibliothèque, sinon la première venue."""
    candidates = []
    for lib in app.materialLibraries:
        try:
            n = lib.appearances.count
        except Exception:  # noqa: BLE001
            continue
        for i in range(min(n, 600)):
            ap = lib.appearances.item(i)
            nom = ap.name.lower()
            score = 0 if any(m in nom for m in ("paint", "peinture", "plastic", "plastique", "enamel")) else 1
            candidates.append((score, i, ap))
            if score == 0 and _propriete_couleur(ap):
                return ap
    for _, _, ap in sorted(candidates, key=lambda c: (c[0], c[1]))[:200]:
        if _propriete_couleur(ap):
            return ap
    for i in range(design.appearances.count):
        ap = design.appearances.item(i)
        if _propriete_couleur(ap):
            return ap
    raise ErreurChants("erreur.apparence")


def apparence_chant(app, design, nom_ref: str, couleur_hexa: str, cache: dict | None = None):
    nom = f"{PREFIXE_APPARENCE} · {nom_ref} · {couleur_hexa}"
    if cache is not None and nom in cache:
        return cache[nom]
    ap = design.appearances.itemByName(nom)
    if ap is None:
        ap = design.appearances.addByCopy(_source_apparence(app, design), nom)
        if ap is None:
            raise ErreurChants("erreur.apparence")
    p = _propriete_couleur(ap)
    if p is not None:
        r, g, b = reglages.rvb(couleur_hexa)
        p.value = adsk.core.Color.create(r, g, b, 255)
    if cache is not None:
        cache[nom] = ap
    return ap


def _a_une_surcharge(face) -> bool:
    try:
        fa, ba = face.appearance, face.body.appearance
        return fa is not None and (ba is None or fa.name != ba.name)
    except Exception:  # noqa: BLE001
        return False


def colorer(app, design, face, d: dict | None = None, cache: dict | None = None) -> None:
    """Pose la couleur de la référence sur la face ; note l'apparence d'origine la première fois."""
    d = d or lire_marque(face)
    if not d:
        return
    if not d.get("colore"):
        d["origine"] = face.appearance.name if _a_une_surcharge(face) else ""
    face.appearance = apparence_chant(app, design, d.get("reference", "?"), d.get("couleur", "#FF7A00"), cache)
    d["colore"] = True
    _ecrire_marque(face, d)


def decolorer(design, face, d: dict | None = None, garder_marque: bool = True) -> None:
    """Rend à la face son apparence d'origine (surcharge retirée, ou apparence notée)."""
    d = d if d is not None else (lire_marque(face) or {})
    if not d.get("colore"):
        return
    origine = d.get("origine") or ""
    ap = design.appearances.itemByName(origine) if origine else None
    try:
        face.appearance = ap  # None : retire la surcharge [supposé]
    except Exception:  # noqa: BLE001 — repli : apparence du corps
        face.appearance = face.body.appearance
    d.pop("colore", None)
    d.pop("origine", None)
    if garder_marque:
        _ecrire_marque(face, d)


def retirer_couleurs(design) -> int:
    n = 0
    for f, d in faces_marquees(design):
        if d.get("colore"):
            decolorer(design, f, d)
            n += 1
    return n


def colorer_tout(app, design) -> int:
    n, cache = 0, {}
    for f, d in faces_marquees(design):
        colorer(app, design, f, d, cache)
        n += 1
    return n


# --- surbrillance (graphiques personnalisés) --------------------------------------------------------------------

def _maillage(face):
    calc = face.meshManager.createMeshCalculator()
    calc.setQuality(adsk.fusion.TriangleMeshQualityOptions.LowQualityTriangleMesh)
    return calc.calculate()


def dessiner_faces(groupe, faces_couleurs) -> int:
    """faces_couleurs : [(face, "#RRGGBB")] ; un maillage coloré par face, posé devant le modèle."""
    n = 0
    for face, couleur in faces_couleurs:
        m = _maillage(face)
        coords = adsk.fusion.CustomGraphicsCoordinates.create(m.nodeCoordinatesAsDouble)
        e = groupe.addMesh(coords, m.nodeIndices, m.normalVectorsAsDouble, m.nodeIndices)
        if e is None:
            continue
        r, g, b = reglages.rvb(couleur)
        e.color = adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(r, g, b, 255))
        try:
            e.depthPriority = 1
        except Exception:  # noqa: BLE001
            pass
        n += 1
    return n


def _groupe_surbrillance(design):
    gs = design.rootComponent.customGraphicsGroups
    for i in range(gs.count):
        g = gs.item(i)
        if g.id == ID_SURBRILLANCE:
            return g
    return None


def surbrillance_active(design) -> bool:
    return _groupe_surbrillance(design) is not None


def basculer_surbrillance(design, forcer: bool | None = None) -> bool:
    """Allume ou éteint la surbrillance des chants marqués ; rend l'état final (True = allumée)."""
    g = _groupe_surbrillance(design)
    allumer = (g is None) if forcer is None else forcer
    if g is not None:
        g.deleteMe()
    if not allumer:
        return False
    g = design.rootComponent.customGraphicsGroups.add()
    g.id = ID_SURBRILLANCE
    faces = []
    for f, d in faces_marquees(design):
        for p in proxys(design, f):
            faces.append((p, d.get("couleur", "#FF7A00")))
    dessiner_faces(g, faces)
    return True


# --- « Tous les chants visibles » -------------------------------------------------------------------------------

def corps_visibles(design):
    racine = design.rootComponent
    r = [b for b in racine.bRepBodies if b.isSolid and b.isVisible]
    for occ in racine.allOccurrences:
        try:
            if not occ.isVisible:
                continue
        except Exception:  # noqa: BLE001
            pass
        r += [b for b in occ.bRepBodies if b.isSolid and b.isVisible]
    return r


def _points_echantillon(face, n=3):
    """Points sur la face (au milieu en v, répartis en u), en cm, repère de l'entité."""
    ev = face.evaluator
    ok, bornes = ev.parametricRange()
    pts = []
    if ok:
        u0, u1 = bornes.minPoint.x, bornes.maxPoint.x
        v0, v1 = bornes.minPoint.y, bornes.maxPoint.y
        for i in range(n):
            par = adsk.core.Point2D.create(u0 + (u1 - u0) * (i + 1) / (n + 1), (v0 + v1) / 2)
            if ev.isParameterOnFace(par):
                ok2, p = ev.getPointAtParameter(par)
                if ok2:
                    pts.append(p)
    return pts or [face.pointOnFace]


def _normale_sortante(face, corps, p):
    ok, n = face.evaluator.getNormalAtPoint(p)
    if not ok:
        return None
    n.normalize()
    q = p.copy()
    v = n.copy()
    v.scaleBy(0.01)
    q.translateBy(v)
    if corps.pointContainment(q) == adsk.fusion.PointContainment.PointInsidePointContainment:
        n.scaleBy(-1)
    return n


def _au_contact(face, corps, autres) -> bool:
    """Vrai si un point juste devant la face (0,05 mm) est dans (ou sur) un autre corps visible."""
    for p in _points_echantillon(face):
        n = _normale_sortante(face, corps, p)
        if n is None:
            continue
        q = p.copy()
        n.scaleBy(0.005)
        q.translateBy(n)
        qmm = _mm(q)
        for b, boite in autres:
            if not chants.point_dans_boite(qmm, boite):
                continue
            if b.pointContainment(q) != adsk.fusion.PointContainment.PointOutsidePointContainment:
                return True
    return False


def chants_visibles(design):
    """(faces de chant libres, nombre de chants au contact exclus) sur tous les corps visibles."""
    corps = corps_visibles(design)
    infos = [(b, info_corps(b)) for b in corps]
    libres, exclus = [], 0
    for b, info in infos:
        if info.axe is None:
            continue
        voisins = [(o, i.boite) for o, i in infos if o is not b and chants.boites_se_touchent(info.boite, i.boite)]
        for f in b.faces:
            genre, d = _genre_direction(f)
            if not chants.est_chant(genre, d, info.axe):
                continue
            if voisins and _au_contact(f, b, voisins):
                exclus += 1
            else:
                libres.append(f)
    return libres, exclus


# --- lecture pour le tableau ------------------------------------------------------------------------------------

def lire_pieces(design) -> list[chants.PieceLue]:
    racine = design.rootComponent
    par_corps = {}
    for f, d in faces_marquees(design):
        corps = f.body
        cle = cle_corps(corps)
        if cle not in par_corps:
            comp = corps.parentComponent
            q = 1 if comp == racine else max(racine.allOccurrencesByComponent(comp).count, 1)
            info = info_corps(corps)
            par_corps[cle] = chants.PieceLue(nom_piece(corps), q, round(info.longueur, 1), round(info.largeur, 1),
                                             round(info.epaisseur, 1))
        par_corps[cle].chants.append(chants.ChantLu(
            ident=d.get("id", ""), reference=d.get("reference", "?"), epaisseur=float(d.get("epaisseur", 0) or 0),
            couleur=d.get("couleur", "#FF7A00"), longueur=round(longueur_face(f), 1), cote=cote_face(f)))
    return sorted(par_corps.values(), key=lambda p: p.nom.lower())


def theme_sombre(app) -> bool:
    try:
        th = app.preferences.generalPreferences.activeUserInterfaceTheme
        T = adsk.core.UserInterfaceThemes
        return th in (getattr(T, "DarkBlueUserInterfaceTheme", None), getattr(T, "DarkGrayUserInterfaceTheme", None))
    except Exception:  # noqa: BLE001
        return False
