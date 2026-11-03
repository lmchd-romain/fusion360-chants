"""Fausse géométrie Fusion (unités internes : cm) : un panneau parallélépipédique et ce que fusion_api en lit."""
import math


class Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    @property
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)


class Pt(Vec):
    def vectorTo(self, o):
        return Vec(o.x - self.x, o.y - self.y, o.z - self.z)


class Boite:
    def __init__(self, a, b):
        self.minPoint, self.maxPoint = a, b


class Attr:
    def __init__(self, conteneur, groupe, nom, valeur):
        self.conteneur, self.groupName, self.name, self.value = conteneur, groupe, nom, valeur
        self.parent = conteneur.parent

    def deleteMe(self):
        del self.conteneur.d[(self.groupName, self.name)]
        return True


class Attributs:
    def __init__(self, parent):
        self.parent, self.d = parent, {}

    def add(self, g, n, v):
        a = self.d.get((g, n))
        if a:
            a.value = v
        else:
            a = self.d[(g, n)] = Attr(self, g, n, v)
        return a

    def itemByName(self, g, n):
        return self.d.get((g, n))


class Apparence:
    def __init__(self, nom):
        self.name = nom


class Arete:
    def __init__(self, geometrie):
        self.geometry = geometrie


class Plan:
    def __init__(self, types, n):
        self.surfaceType = types.PlaneSurfaceType
        self.normal = n


def panneau(adsk, L, W, E, nom="Côté", ox=0.0):
    """Panneau L × W × E mm (posé à plat, x = longueur), décalé de ox mm ; rend le corps."""
    c = lambda mm: mm / 10.0
    ST = adsk.core.SurfaceTypes
    Line3D = adsk.core.Line3D
    BRepFace = adsk.fusion.BRepFace
    x0, x1, y1, z1 = c(ox), c(ox + L), c(W), c(E)

    def ligne(a, b):
        g = Line3D()
        g.startPoint, g.endPoint = Pt(*a), Pt(*b)
        return Arete(g)

    corps = type("Corps", (), {})()
    corps.name, corps.isSolid, corps.assemblyContext, corps.entityToken = nom, True, None, f"jeton-{nom}"
    corps.appearance = Apparence("Chêne")
    corps.vertices = [Arete(Pt(x, y, z)) for x in (x0, x1) for y in (0, y1) for z in (0, z1)]
    corps.boundingBox = Boite(Pt(x0, 0, 0), Pt(x1, y1, z1))
    faces = []
    defs = [  # normale, aire (cm²), point, arêtes
        ((0, 0, 1), c(L) * c(W), (x0 + c(L) / 2, y1 / 2, z1), [ligne((x0, 0, z1), (x1, 0, z1)), ligne((x0, 0, z1), (x0, y1, z1))]),
        ((0, 0, -1), c(L) * c(W), (x0 + c(L) / 2, y1 / 2, 0), []),
        ((0, -1, 0), c(L) * z1, (x0 + c(L) / 2, 0, z1 / 2), []),
        ((0, 1, 0), c(L) * z1, (x0 + c(L) / 2, y1, z1 / 2), []),
        ((-1, 0, 0), y1 * z1, (x0, y1 / 2, z1 / 2), []),
        ((1, 0, 0), y1 * z1, (x1, y1 / 2, z1 / 2), []),
    ]
    for i, (n, aire, p, aretes) in enumerate(defs):
        f = BRepFace()
        f.geometry = Plan(ST, Vec(*n))
        f.area, f.pointOnFace, f.edges, f.body = aire, Pt(*p), aretes, corps
        f.assemblyContext, f.tempId, f.attributes = None, i, None
        f.attributes = Attributs(f)
        f.appearance = corps.appearance
        faces.append(f)
    corps.faces = faces
    return corps


class Design:
    """Document : racine, apparences, attributs du design, recherche d'attributs sur les faces des corps."""

    def __init__(self, corps):
        self.corps = corps
        self.rootComponent = racine = type("Racine", (), {})()
        racine.name = "Racine"
        racine.parentDesign = self
        for b in corps:
            b.parentComponent = racine
        self.attributes = Attributs(self)
        self.apparences = {}
        d = self

        class Apps:
            count = 0

            def itemByName(self, nom):
                return d.apparences.get(nom)

        self.appearances = Apps()

    def findAttributes(self, g, n):
        return [f.attributes.itemByName(g, n) for b in self.corps for f in b.faces if f.attributes.itemByName(g, n)]
