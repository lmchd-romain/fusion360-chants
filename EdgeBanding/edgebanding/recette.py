"""Recette automatique, jouée DANS Fusion (connecteur Fusion MCP) : sondes P1 à P3 et vérifications V1 à V7.

Usage (dans Fusion, add-in démarré) :
    import sys, json; r = sys.modules["edgebanding.recette"].jouer(); print(json.dumps(r, ensure_ascii=False, indent=1))

Crée UN nouveau document (jamais enregistré), y construit les pièces d'essai par script, puis joue chaque scénario.
Rapport JSON dans essai/resultats/recette-<horodatage>.json (à côté du dossier EdgeBanding). Ne modifie aucun autre
document. P4 (couleur sur une mise en plan) se juge à l'œil : geste manuel M4.
"""
from __future__ import annotations

import json
import math
import time
import traceback
from datetime import datetime
from pathlib import Path

import adsk.core
import adsk.fusion

from . import VERSION, fusion_api, reglages, tableau
from .pinceau import appliquer
from .textes import Textes

RACINE = Path(__file__).resolve().parents[1]
RESULTATS = RACINE.parent / "essai" / "resultats"
CM = 0.1  # mm → cm
ABS2 = {"cle": "abs2-blanc", "nom": "ABS 2 mm blanc", "epaisseur": 2.0, "couleur": "orange"}
ABS08 = {"cle": "abs08-blanc", "nom": "ABS 0,8 mm blanc", "epaisseur": 0.8, "couleur": "jaune"}
NB_TASSEAUX = 10


# --- construction des pièces d'essai --------------------------------------------------------------------------

def _p(x, y, z=0.0):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def _decale(x_mm, y_mm=0.0, z_mm=0.0):
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(x_mm * CM, y_mm * CM, z_mm * CM)
    return m


def _extruder(comp, esq, z0, dz, nom):
    entree = comp.features.extrudeFeatures.createInput(esq.profiles.item(0),
                                                       adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    entree.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dz * CM))
    if z0:
        entree.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(z0 * CM))
    ext = comp.features.extrudeFeatures.add(entree)
    corps = ext.bodies.item(0)
    corps.name = nom
    return corps, ext


def _boite(comp, x0, y0, z0, dx, dy, dz, nom):
    esq = comp.sketches.add(comp.xYConstructionPlane)
    esq.sketchCurves.sketchLines.addTwoPointRectangle(_p(x0, y0), _p(x0 + dx, y0 + dy))
    return _extruder(comp, esq, z0, dz, nom)


def _composant(racine, nom, transfo=None):
    occ = racine.occurrences.addNewComponent(transfo or adsk.core.Matrix3D.create())
    occ.component.name = nom
    return occ


# --- scénarios ------------------------------------------------------------------------------------------------

def _scenario(rapport, nom, fn):
    t0 = time.perf_counter()
    try:
        r = fn()
        r = r if isinstance(r, dict) else {"ok": bool(r)}
    except Exception:  # noqa: BLE001
        r = {"ok": False, "erreur": traceback.format_exc()}
    r["ms"] = round((time.perf_counter() - t0) * 1000)
    rapport["scenarios"][nom] = r
    adsk.doEvents()
    return r


def _ids(design):
    return [d.get("id") for _, d in fusion_api.faces_marquees(design)]


def jouer() -> dict:
    app = adsk.core.Application.get()
    t = Textes(RACINE / "ressources" / "langues", "fr")
    rapport = {"plugin": "EdgeBanding", "version": VERSION, "fusion": app.version,
               "date": datetime.now().isoformat(timespec="seconds"), "scenarios": {}}
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    racine = design.rootComponent
    fusion_api.vider_cache()
    P = {}       # corps (proxys dans l'assemblage) par nom
    E = {}       # extrusions utiles
    etat = {"marques": {}, "entites": {}}
    biblio = [ABS2, ABS08]

    def construire():
        occ = _composant(racine, "Côté gauche")
        _boite(occ.component, 0, 0, 0, 18, 560, 720, "Côté gauche")
        P["cote_g"] = occ.bRepBodies.item(0)
        occ = _composant(racine, "Côté droit")
        _boite(occ.component, 582, 0, 0, 18, 560, 720, "Côté droit")
        P["cote_d"] = occ.bRepBodies.item(0)
        occ = _composant(racine, "Dessous")
        _boite(occ.component, 18, 0, 0, 564, 560, 18, "Dessous")
        P["dessous"] = occ.bRepBodies.item(0)
        occ = _composant(racine, "Étagère")
        _, E["etagere"] = _boite(occ.component, 1000, 0, 0, 800, 300, 19, "Étagère")
        P["etagere"] = occ.bRepBodies.item(0)
        occ = _composant(racine, "Porte")
        _boite(occ.component, 0, -1200, 0, 397, 716, 19, "Porte")
        P["porte_1"] = occ.bRepBodies.item(0)
        occ2 = racine.occurrences.addExistingComponent(occ.component, _decale(500))
        P["porte_2"] = occ2.bRepBodies.item(0)
        occ = _composant(racine, "Plateau rond")
        esq = occ.component.sketches.add(occ.component.xYConstructionPlane)
        esq.sketchCurves.sketchCircles.addByCenterRadius(_p(2200, 300), 200 * CM)
        _extruder(occ.component, esq, 0, 25, "Plateau rond")
        P["rond"] = occ.bRepBodies.item(0)
        for i in range(NB_TASSEAUX):
            P[f"tasseau_{i}"], _ = _boite(racine, 3000, i * 100, 0, 300, 40, 20, f"Tasseau {i}")
        app.activeViewport.fit()
        return {"ok": True, "pieces": len(P)}

    if not _scenario(rapport, "construction", construire)["ok"]:
        return _ecrire(rapport)

    def v1_detection():
        attendu = {"cote_g": 4, "dessous": 4, "etagere": 4, "porte_1": 4, "rond": 1, "tasseau_0": 4}
        res, ok = {}, True
        for cle, n in attendu.items():
            b = P[cle]
            ch = [f for f in b.faces if fusion_api.est_face_chant(f)]
            info = fusion_api.info_corps(b)
            longs = sorted(round(fusion_api.longueur_face(f), 1) for f in ch)
            res[cle] = {"chants": len(ch), "faces": b.faces.count, "longueurs": longs,
                        "dims": [round(info.longueur, 1), round(info.largeur, 1), round(info.epaisseur, 1)]}
            ok &= len(ch) == n
        ok &= res["cote_g"]["longueurs"] == [560.0, 560.0, 720.0, 720.0]
        ok &= res["cote_g"]["dims"] == [720.0, 560.0, 18.0]
        ok &= abs(res["rond"]["longueurs"][0] - math.pi * 400) < 0.5
        return {"ok": ok, **res}

    def v2_tous_visibles():
        libres, exclus = fusion_api.chants_visibles(design)
        for f in libres:
            k = fusion_api.cle_face(f)
            if k not in etat["marques"]:
                etat["marques"][k] = ABS2["cle"]
                etat["entites"][k] = fusion_api.proxys(design, fusion_api.natif(f))
        attendu = 4 + 4 + 2 + 4 + 4 + 1 + 4 * NB_TASSEAUX
        return {"ok": len(etat["marques"]) == attendu and exclus == 2, "chants_uniques": len(etat["marques"]),
                "attendu": attendu, "faces_libres_proxys": len(libres), "au_contact_exclus": exclus}

    def p1_fluidite():
        faces = [etat["entites"][k][0] for k in list(etat["marques"])[:50]]
        t0 = time.perf_counter()
        for f in faces:  # travail d'un clic : survol, clé, apparitions
            fusion_api.est_face_chant(f)
            fusion_api.proxys(design, fusion_api.natif(f))
            fusion_api.cle_face(f)
        ms_clic = (time.perf_counter() - t0) * 1000 / max(len(faces), 1)
        g = racine.customGraphicsGroups.add()
        t0 = time.perf_counter()
        n = fusion_api.dessiner_faces(g, [(f, "#FF7A00") for f in faces])
        ms_apercu = (time.perf_counter() - t0) * 1000
        g.deleteMe()
        # dernier tasseau en ABS 0,8 : deux références dans le document
        for f in P[f"tasseau_{NB_TASSEAUX - 1}"].faces:
            k = fusion_api.cle_face(f)
            if k in etat["marques"]:
                etat["marques"][k] = ABS08["cle"]
        t0 = time.perf_counter()
        bilan = appliquer(app, design, etat["marques"], etat["entites"], {}, biblio, "couleur")
        ms_ok = (time.perf_counter() - t0) * 1000
        return {"ok": ms_clic < 100 and ms_apercu < 1000 and bilan["marques"] == len(etat["marques"]),
                "ms_par_clic": round(ms_clic, 1), "ms_apercu_50_faces": round(ms_apercu), "faces_apercu": n,
                "ms_appliquer_tout": round(ms_ok), "bilan": bilan}

    def v3_couleur():
        f = next(f for f in P["cote_g"].faces if fusion_api.est_face_chant(f))
        ap = f.appearance
        prop = fusion_api._propriete_couleur(ap)
        coul = prop.value if prop else None
        rvb = (coul.red, coul.green, coul.blue) if coul else None
        attendu = reglages.rvb(reglages.hexa("orange"))
        apps = [design.appearances.item(i).name for i in range(design.appearances.count)
                if design.appearances.item(i).name.startswith(fusion_api.PREFIXE_APPARENCE)]
        dessus = max(P["cote_g"].faces, key=lambda x: x.area)
        return {"ok": ap.name.startswith(fusion_api.PREFIXE_APPARENCE) and rvb == attendu and len(apps) == 2
                and not dessus.appearance.name.startswith(fusion_api.PREFIXE_APPARENCE),
                "apparence": ap.name, "rvb": rvb, "apparences_creees": apps, "propriete": prop.id if prop else None}

    def p3_composant_deux_fois():
        f1 = next(f for f in P["porte_1"].faces if fusion_api.est_face_chant(f))
        f2 = fusion_api.proxys(design, fusion_api.natif(f1))
        noms = [p.appearance.name for p in f2]
        return {"ok": len(f2) == 2 and len(set(noms)) == 1 and noms[0].startswith(fusion_api.PREFIXE_APPARENCE),
                "apparitions": len(f2), "apparences": noms,
                "reponse": "les deux occurrences changent ensemble" if len(set(noms)) == 1 else "occurrences distinctes"}

    def v4_tableau():
        fusion_api.vider_cache()
        pieces, disparus, sorties = tableau.ecrire_fichiers(design, "Recette chants", 40, True, True, True, t,
                                                            RESULTATS)
        par_nom = {p.nom: p for p in pieces}
        porte, dessous, rond = par_nom.get("Porte"), par_nom.get("Dessous"), par_nom.get("Plateau rond")
        csv = sorties["csv"].read_bytes()
        from .chants import debit, totaux
        tot = {(x.reference, x.epaisseur): x for x in totaux(pieces, 40)}
        ok = (porte is not None and porte.quantite == 2 and dessous is not None
              and (dessous.longueur, dessous.largeur, dessous.epaisseur) == (564.0, 560.0, 18.0)
              and len(dessous.chants) == 2 and debit(dessous) == (564.0, 556.0)
              and rond is not None and rond.chants[0].cote is None and csv.startswith(b"\xef\xbb\xbf")
              and tot[("ABS 0,8 mm blanc", 0.8)].nombre == 4 and not disparus)
        return {"ok": ok, "pieces": [(p.nom, p.quantite, p.longueur, p.largeur, p.epaisseur, len(p.chants)) for p in pieces],
                "totaux": {f"{k[0]}": (v.nombre, round(v.longueur_nette), round(v.longueur_avec_marge)) for k, v in tot.items()},
                "fichiers": {k: str(v) for k, v in sorties.items()}}

    def v5_surbrillance():
        allume = fusion_api.basculer_surbrillance(design)
        g = fusion_api._groupe_surbrillance(design)
        n = g.count if g else 0
        eteint = not fusion_api.basculer_surbrillance(design)
        attendu = sum(len(v) for v in etat["entites"].values())
        return {"ok": allume and eteint and n == attendu and fusion_api._groupe_surbrillance(design) is None,
                "graphiques": n, "attendu": attendu}

    def p2_survie():
        id_ = None
        face = None
        for f in P["etagere"].faces:
            d = fusion_api.lire_marque(f)
            if d and fusion_api.cote_face(f) in ("+v", "-v") and abs(fusion_api.longueur_face(f) - 800) < 0.5:
                id_, face = d["id"], f
                break
        res = {"id": id_}
        comp = fusion_api.natif(P["etagere"]).parentComponent
        dist = adsk.fusion.DistanceExtentDefinition.cast(E["etagere"].extentOne)
        dist.distance.expression = "22 mm"
        res["a_epaisseur_changee"] = _ids(design).count(id_)
        design.timeline.moveToBeginning()
        design.timeline.moveToEnd()
        res["b_timeline_reculee"] = _ids(design).count(id_)
        esq = comp.sketches.add(comp.xYConstructionPlane)
        esq.sketchCurves.sketchLines.addTwoPointRectangle(_p(1350, -10), _p(1450, 20))
        entree = comp.features.extrudeFeatures.createInput(esq.profiles.item(0),
                                                           adsk.fusion.FeatureOperations.CutFeatureOperation)
        entree.setDistanceExtent(False, adsk.core.ValueInput.createByReal(5.0))
        comp.features.extrudeFeatures.add(entree)
        res["c_entaille_dans_le_chant"] = _ids(design).count(id_)
        fusion_api.vider_cache()
        res["ok"] = res["a_epaisseur_changee"] == 1 and res["b_timeline_reculee"] == 1
        res["note"] = "c : nombre de faces qui gardent l'attribut après une entaille qui coupe le chant en deux"
        return res

    def v6_disparus():
        fusion_api.ecrire_registre(design)
        racine.bRepBodies.itemByName("Tasseau 0").deleteMe()  # corps relu : la découpe de P2 invalide les anciens
        perdus = fusion_api.chants_disparus(design)
        return {"ok": len(perdus) == 4 and all(p["piece"] == "Tasseau 0" for p in perdus), "disparus": perdus}

    def v7_retirer_couleurs():
        n = fusion_api.retirer_couleurs(design)
        restes = [f for f, d in fusion_api.faces_marquees(design)
                  if f.appearance and f.appearance.name.startswith(fusion_api.PREFIXE_APPARENCE)]
        f = next((f for f, _ in fusion_api.faces_marquees(design)), None)
        return {"ok": n > 0 and not restes and (f is None or fusion_api.lire_marque(f) is not None),
                "chants_decolores": n, "faces_encore_colorees": len(restes),
                "marque_gardee": f is not None and fusion_api.lire_marque(f) is not None}

    for nom, fn in (("V1_detection", v1_detection), ("V2_tous_les_chants_visibles", v2_tous_visibles),
                    ("P1_fluidite_50_chants", p1_fluidite), ("V3_couleur_sur_les_faces", v3_couleur),
                    ("P3_composant_deux_fois", p3_composant_deux_fois), ("V4_tableau_csv", v4_tableau),
                    ("V5_surbrillance", v5_surbrillance), ("P2_survie_des_attributs", p2_survie),
                    ("V6_chants_disparus", v6_disparus)):
        _scenario(rapport, nom, fn)
    # V7 en dernier mais on remet les couleurs pour que l'utilisateur voie le résultat (geste M2)
    _scenario(rapport, "V7_retirer_couleurs", v7_retirer_couleurs)
    try:
        fusion_api.colorer_tout(app, design)
    except Exception:  # noqa: BLE001
        pass
    app.activeViewport.fit()
    return _ecrire(rapport)


def _ecrire(rapport) -> dict:
    rapport["bilan"] = {n: s.get("ok") for n, s in rapport["scenarios"].items()}
    rapport["tout_ok"] = all(rapport["bilan"].values())
    try:
        RESULTATS.mkdir(parents=True, exist_ok=True)
        f = RESULTATS / f"recette-{datetime.now():%Y%m%d-%H%M%S}.json"
        f.write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        rapport["fichier"] = str(f)
    except OSError as e:
        rapport["fichier"] = f"non écrit : {e}"
    return rapport
