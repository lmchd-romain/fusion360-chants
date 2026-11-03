"""Commande « Chants plaqués » : le pinceau.

Un clic sur un chant le plaque avec la référence choisie ; un nouveau clic le retire (gomme). Bouton « Tous les chants
visibles ». Aperçu en couleur par graphiques personnalisés ; à OK, attributs posés sur les faces et, selon le mode,
couleur réelle sur les faces. Tout se fait dans `execute` : une seule étape d'annulation.
"""
from __future__ import annotations

import time

import adsk.core
import adsk.fusion

from . import chants, contexte as ctx, fusion_api, reglages

handlers_dialogue = []
_etat: dict = {}

LIMITE_APERCU = 400  # faces dessinées au plus dans l'aperçu


# --- outils -----------------------------------------------------------------------------------------------------

def _biblio() -> list[dict]:
    return _etat["biblio"]


def _ref(cle) -> dict:
    return next((r for r in _biblio() if r["cle"] == cle), _biblio()[0])


def _couleur_de_hexa(h: str) -> str:
    h = (h or "").upper()
    return next((n for n, v in reglages.COULEURS.items() if v.upper() == h), "orange")


def _remplir_references(inputs):
    dd = _etat["champs"]["reference"]
    _etat["silence"] = True
    try:
        dd.listItems.clear()
        for r in _biblio():
            dd.listItems.add(r["nom"], r["cle"] == _etat["ref"])
        dd.listItems.add(ctx.t("dialogue.nouvelle_ref"), False)
    finally:
        _etat["silence"] = False


def _remplir_edition():
    c = _etat["champs"]
    r = _ref(_etat["ref"])
    _etat["silence"] = True
    try:
        c["ref_nom"].value = r["nom"]
        c["ref_ep"].value = r["epaisseur"] / 10.0
        for i in range(c["ref_couleur"].listItems.count):
            it = c["ref_couleur"].listItems.item(i)
            it.isSelected = list(reglages.COULEURS)[i] == r["couleur"]
    finally:
        _etat["silence"] = False


def _longueur(k) -> float:
    L = _etat["longueurs"].get(k)
    if L is None:
        try:
            L = fusion_api.longueur_face(_etat["entites"][k][0])
        except Exception:  # noqa: BLE001
            L = 0.0
        _etat["longueurs"][k] = L
    return L


def _resume():
    t = ctx.t
    liste = [(_ref(cle)["nom"], _longueur(k)) for k, cle in _etat["marques"].items()]
    txt = chants.resume(liste, t)
    if _etat.get("message"):
        txt += "\n" + _etat["message"]
    if _etat.get("disparus"):
        txt += "\n⚠ " + t("pinceau.disparus", n=len(_etat["disparus"]))
    _etat["champs"]["resume"].text = txt


def _reconstruire_selection():
    sel = _etat["champs"]["chants"]
    _etat["reconstruction"] = True
    try:
        sel.clearSelection()
        for k in _etat["marques"]:
            for e in _etat["entites"][k]:
                sel.addSelection(e)
    finally:
        _etat["reconstruction"] = False


def _ajouter(face) -> bool:
    k = fusion_api.cle_face(face)
    if k in _etat["marques"]:
        return False
    _etat["marques"][k] = _etat["ref"]
    _etat["entites"][k] = fusion_api.proxys(_etat["design"], fusion_api.natif(face))
    return True


def _selection_changee():
    """Compare la sélection à l'état : ajouts → référence courante ; une apparition retirée → chant retiré (gomme)."""
    if _etat.get("reconstruction"):
        return
    sel = _etat["champs"]["chants"]
    present = {}
    for i in range(sel.selectionCount):
        e = adsk.fusion.BRepFace.cast(sel.selection(i).entity)
        if e is not None:
            present.setdefault(fusion_api.cle_face(e), []).append(e)
    change = False
    retires = set()
    for k in list(_etat["marques"]):
        if len(present.get(k, [])) < len(_etat["entites"][k]):
            del _etat["marques"][k]  # une seule apparition retirée suffit : le chant part de toutes les occurrences
            retires.add(k)
            change = True
    for k, ents in present.items():
        if k not in _etat["marques"] and k not in retires:
            if fusion_api.est_face_chant(ents[0]):
                change |= _ajouter(ents[0])
            else:
                change = True  # face refusée : la reconstruction la retire
    voulu = sum(len(_etat["entites"][k]) for k in _etat["marques"])
    if change or voulu != sel.selectionCount:
        _reconstruire_selection()
    _etat["message"] = ""


def _tous_visibles():
    t0 = time.perf_counter()
    libres, exclus = fusion_api.chants_visibles(_etat["design"])
    n = sum(1 for f in libres if _ajouter(f))
    _reconstruire_selection()
    _etat["message"] = ctx.t("pinceau.tous_resultat", n=n, x=exclus)
    ctx.log.info("Tous les chants visibles : %d ajoutés, %d au contact exclus, %.0f ms", n, exclus,
                 (time.perf_counter() - t0) * 1000)


# --- dialogue ---------------------------------------------------------------------------------------------------

class QuandCree(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        ctx.garde(lambda: _creer_dialogue(args.command))


def _creer_dialogue(cmd):
    t = ctx.t
    handlers_dialogue.clear()
    _etat.clear()
    fusion_api.vider_cache()
    design = ctx.design_actif()
    rg = reglages.lire(ctx.FICHIER_REGLAGES, t)
    _etat.update({"design": design, "biblio": rg["bibliotheque"], "ref": rg["reference"], "marques": {},
                  "entites": {}, "initiales": {}, "longueurs": {}, "champs": {},
                  "message": "", "disparus": []})
    inputs = cmd.commandInputs
    c = _etat["champs"]
    c["reference"] = dd = inputs.addDropDownCommandInput("reference", t("dialogue.reference"),
                                                         adsk.core.DropDownStyles.TextListDropDownStyle)
    dd.tooltip = t("dialogue.reference_infobulle")
    c["chants"] = sel = inputs.addSelectionInput("chants", t("dialogue.chants"), t("dialogue.chants_infobulle"))
    sel.addSelectionFilter("SolidFaces")
    sel.setSelectionLimits(0, 0)
    sel.tooltip = t("dialogue.chants_infobulle")
    c["tous"] = b = inputs.addBoolValueInput("tous", t("dialogue.tous"), False, str(ctx.RESSOURCES / "boutons" / "tous"),
                                             False)
    b.tooltip = t("dialogue.tous_infobulle")
    c["resume"] = inputs.addTextBoxCommandInput("resume", "", t("resume.vide"), 3, True)
    g = inputs.addGroupCommandInput("affichage", t("dialogue.affichage"))
    g.isExpanded = True
    c["mode"] = m = g.children.addDropDownCommandInput("mode", t("dialogue.mode"),
                                                       adsk.core.DropDownStyles.TextListDropDownStyle)
    for mode in reglages.MODES:
        m.listItems.add(t(f"mode.{mode}"), mode == rg["mode"])
    m.tooltip = t("dialogue.mode_infobulle")
    g = inputs.addGroupCommandInput("ref_edit", t("dialogue.ref_edit"))
    g.isExpanded = False
    c["ref_edit"] = g
    c["ref_nom"] = g.children.addStringValueInput("ref_nom", t("dialogue.ref_nom"), "")
    c["ref_ep"] = v = g.children.addValueInput("ref_ep", t("dialogue.ref_ep"), "mm",
                                               adsk.core.ValueInput.createByString("2 mm"))
    v.tooltip = t("dialogue.ref_ep_infobulle")
    c["ref_couleur"] = dc = g.children.addDropDownCommandInput("ref_couleur", t("dialogue.ref_couleur"),
                                                               adsk.core.DropDownStyles.TextListDropDownStyle)
    for nom in reglages.COULEURS:
        dc.listItems.add(t(f"couleur.{nom}"), False)
    dc.tooltip = t("dialogue.ref_couleur_infobulle")

    # chants déjà plaqués : repris dans la sélection (un clic dessus les retire)
    if design is not None:
        for f, d in fusion_api.faces_marquees(design):
            k = fusion_api.cle_face(f)
            cle = d.get("cle")
            if not any(r["cle"] == cle for r in _biblio()):
                cle = cle or reglages.nouvelle_cle(_biblio(), d.get("reference", "ref"))
                _biblio().append({"cle": cle, "nom": d.get("reference") or cle, "epaisseur": float(d.get("epaisseur") or 1),
                                  "couleur": _couleur_de_hexa(d.get("couleur"))})
            _etat["marques"][k] = cle
            _etat["initiales"][k] = f
            _etat["entites"][k] = fusion_api.proxys(design, f)
        _etat["disparus"] = fusion_api.chants_disparus(design)
    _remplir_references(inputs)
    _remplir_edition()
    if _etat["marques"]:
        _reconstruire_selection()
    _resume()

    for evenement, classe in ((cmd.inputChanged, _QuandChange), (cmd.validateInputs, _QuandValide),
                              (cmd.preSelect, _QuandPreSelect), (cmd.executePreview, _QuandApercu),
                              (cmd.execute, _QuandExecute), (cmd.destroy, _QuandDetruit)):
        h = classe()
        evenement.add(h)
        handlers_dialogue.append(h)


class _QuandPreSelect(adsk.core.SelectionEventHandler):
    """N'allume au survol que les chants (faces perpendiculaires au panneau, ou chants cintrés)."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            f = adsk.fusion.BRepFace.cast(args.selection.entity)
            if f is None or not fusion_api.est_face_chant(f):
                args.isSelectable = False
        except Exception:  # noqa: BLE001
            args.isSelectable = False


class _QuandChange(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        if _etat.get("silence"):
            return
        ctx.garde(lambda: _changer(args.input))


def _changer(inp):
    c = _etat["champs"]
    if inp.id == "chants":
        _selection_changee()
    elif inp.id == "tous":
        _tous_visibles()
    elif inp.id == "reference":
        i = inp.selectedItem.index if inp.selectedItem else 0
        if i >= len(_biblio()):  # « Nouvelle référence… »
            base = _ref(_etat["ref"])
            pris = {r["couleur"] for r in _biblio()}
            couleur = next((n for n in reglages.COULEURS if n not in pris), "orange")
            nom = ctx.t("ref.nouvelle")
            r = {"cle": reglages.nouvelle_cle(_biblio(), nom), "nom": nom, "epaisseur": base["epaisseur"],
                 "couleur": couleur}
            _biblio().append(r)
            _etat["ref"] = r["cle"]
            _remplir_references(None)
            c["ref_edit"].isExpanded = True
        else:
            _etat["ref"] = _biblio()[i]["cle"]
        _remplir_edition()
    elif inp.id in ("ref_nom", "ref_ep", "ref_couleur"):
        r = _ref(_etat["ref"])
        if inp.id == "ref_nom" and inp.value.strip():
            r["nom"] = inp.value.strip()
            i = _biblio().index(r)
            _etat["silence"] = True
            try:
                c["reference"].listItems.item(i).name = r["nom"]
            finally:
                _etat["silence"] = False
        elif inp.id == "ref_ep" and inp.isValidExpression and 0 < inp.value * 10.0 <= 20:
            r["epaisseur"] = round(inp.value * 10.0, 3)
        elif inp.id == "ref_couleur" and inp.selectedItem:
            r["couleur"] = list(reglages.COULEURS)[inp.selectedItem.index]
    _resume()


class _QuandValide(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            ep = _etat["champs"]["ref_ep"]
            args.areInputsValid = bool(ep.isValidExpression and 0 < ep.value * 10.0 <= 20
                                       and _etat["champs"]["ref_nom"].value.strip())
        except Exception:  # noqa: BLE001
            args.areInputsValid = True


class _QuandApercu(adsk.core.CommandEventHandler):
    """Aperçu : chaque chant peint dans la couleur de sa référence (graphiques, rien n'est modifié)."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        def dessiner():
            t0 = time.perf_counter()
            g = _etat["design"].rootComponent.customGraphicsGroups.add()
            faces = []
            for k, cle in _etat["marques"].items():
                coul = reglages.hexa(_ref(cle)["couleur"])
                faces += [(e, coul) for e in _etat["entites"][k]]
            n = fusion_api.dessiner_faces(g, faces[:LIMITE_APERCU])
            ctx.log.info("Aperçu : %d faces en %.0f ms", n, (time.perf_counter() - t0) * 1000)
        ctx.garde(dessiner)


class _QuandDetruit(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        _etat.clear()


class _QuandExecute(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            executer()
        except fusion_api.ErreurChants as e:
            args.executeFailed = True
            args.executeFailedMessage = ctx.texte_erreur(e)
        except Exception:  # noqa: BLE001
            ctx.log.exception("Erreur à l'exécution")
            args.executeFailed = True
            args.executeFailedMessage = ctx.t("erreur.inattendu")


def appliquer(app, design, marques: dict, entites: dict, initiales: dict, biblio: list[dict], mode: str) -> dict:
    """Écrit l'état voulu dans le document. marques : clé → clé de référence ; rend un petit bilan.

    Séparé du dialogue pour que la recette l'appelle telle quelle.
    """
    par_cle = {r["cle"]: r for r in biblio}
    cache = {}
    bilan = {"marques": 0, "retires": 0, "colores": 0, "echecs": 0}
    for k, cle in marques.items():
        f = entites[k][0]
        try:
            d = fusion_api.marquer(f, par_cle.get(cle, biblio[0]))
            if mode == "couleur":
                fusion_api.colorer(app, design, f, d, cache)
                bilan["colores"] += 1
            else:
                fusion_api.decolorer(design, f, d)
            bilan["marques"] += 1
        except fusion_api.ErreurChants:
            raise
        except Exception:  # noqa: BLE001 — face d'un composant externe, verrouillée…
            ctx.log.exception("Chant non marqué")
            bilan["echecs"] += 1
    for k, f in initiales.items():
        if k in marques:
            continue
        d = fusion_api.lire_marque(f) or {}
        fusion_api.decolorer(design, f, d, garder_marque=False)
        fusion_api.demarquer(f)
        bilan["retires"] += 1
    if bilan["echecs"]:
        raise fusion_api.ErreurChants("erreur.marquage_n", n=bilan["echecs"])
    fusion_api.ecrire_registre(design)
    if fusion_api.surbrillance_active(design):
        fusion_api.basculer_surbrillance(design, True)
    return bilan


def executer():
    t0 = time.perf_counter()
    design = _etat.get("design") or ctx.design_actif()
    if design is None:
        raise fusion_api.ErreurChants("erreur.pas_de_design")
    m = _etat["champs"]["mode"]
    mode = reglages.MODES[m.selectedItem.index if m.selectedItem else 0]
    bilan = appliquer(ctx.app, design, _etat["marques"], _etat["entites"], _etat["initiales"], _biblio(), mode)
    rg = reglages.lire(ctx.FICHIER_REGLAGES, ctx.t)
    rg.update({"bibliotheque": _biblio(), "reference": _etat["ref"], "mode": mode})
    reglages.ecrire(ctx.FICHIER_REGLAGES, rg)
    ctx.log.info("Pinceau exécuté en %.0f ms : %s", (time.perf_counter() - t0) * 1000, bilan)
