"""Commande « Tableau des chants » : longueurs par référence, marge, débit, export CSV (Excel) et page HTML."""
from __future__ import annotations

import re
import time
import webbrowser

import adsk.core

from . import chants, contexte as ctx, export, fusion_api, reglages

_handlers = []
_etat: dict = {}


def _nom_fichier(texte: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", texte).strip() or "EdgeBanding"


def texte_resume(pieces, disparus, marge, t) -> str:
    tot = chants.totaux(pieces, marge)
    if not tot:
        lignes = [t("tableau.aucun")]
    else:
        lignes = [t("tableau.ligne_total", ref=x.reference, n=x.nombre, m=t.nombre(x.longueur_avec_marge / 1000, 2))
                  for x in tot]
        lignes.append(t("tableau.pieces", n=sum(p.quantite for p in pieces)))
    if disparus:
        lignes.append("⚠ " + t("tableau.disparus", n=len(disparus)))
    return "\n".join(lignes)


def ecrire_fichiers(design, document: str, marge: float, avec_debit: bool, csv: bool, page: bool, t, dossier=None):
    """Écrit le CSV et/ou la page ; rend (pieces, disparus, {"csv": chemin, "html": chemin})."""
    dossier = dossier or ctx.DOSSIER_SORTIE
    pieces = fusion_api.lire_pieces(design)
    disparus = fusion_api.chants_disparus(design)
    sorties = {}
    base = dossier / _nom_fichier(f"{document} - {t('tableau.fichier')}")
    if csv or page:
        dossier.mkdir(parents=True, exist_ok=True)
    if csv:
        f = base.with_suffix(".csv")
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(export.ecrire_csv(pieces, marge, avec_debit, t, disparus))
        sorties["csv"] = f
    if page:
        f = base.with_suffix(".html")
        f.write_text(export.ecrire_html(pieces, marge, avec_debit, t, document, disparus), encoding="utf-8")
        sorties["html"] = f
    return pieces, disparus, sorties


class QuandCree(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        ctx.garde(lambda: _creer_dialogue(args.command))


def _creer_dialogue(cmd):
    t = ctx.t
    _handlers.clear()
    _etat.clear()
    fusion_api.vider_cache()
    rg = reglages.lire(ctx.FICHIER_REGLAGES, t)
    design = ctx.design_actif()
    _etat["design"] = design
    _etat["pieces"] = fusion_api.lire_pieces(design) if design else []
    _etat["disparus"] = fusion_api.chants_disparus(design) if design else []
    inputs = cmd.commandInputs
    _etat["resume"] = inputs.addTextBoxCommandInput("resume", t("tableau.resume"), "", 6, True)
    _etat["marge"] = v = inputs.addValueInput("marge", t("dialogue.marge"), "mm",
                                             adsk.core.ValueInput.createByString(f"{rg['marge']} mm"))
    v.tooltip = t("dialogue.marge_infobulle")
    _etat["debit"] = b = inputs.addBoolValueInput("debit", t("dialogue.debit"), True, "", rg["debit"])
    b.tooltip = t("dialogue.debit_infobulle")
    _etat["html"] = inputs.addBoolValueInput("html", t("dialogue.html"), True, "", rg["html"])
    _etat["csv"] = inputs.addBoolValueInput("csv", t("dialogue.csv"), True, "", rg["csv"])
    _rafraichir()
    for evenement, classe in ((cmd.inputChanged, _QuandChange), (cmd.validateInputs, _QuandValide),
                              (cmd.execute, _QuandExecute), (cmd.destroy, _QuandDetruit)):
        h = classe()
        evenement.add(h)
        _handlers.append(h)


def _marge_mm() -> float:
    v = _etat["marge"]
    return max(v.value * 10.0, 0.0) if v.isValidExpression else 0.0


def _rafraichir():
    _etat["resume"].text = texte_resume(_etat["pieces"], _etat["disparus"], _marge_mm(), ctx.t)


class _QuandChange(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        if args.input.id == "marge":
            ctx.garde(_rafraichir)


class _QuandValide(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            args.areInputsValid = bool(_etat["marge"].isValidExpression and _etat["marge"].value >= 0
                                       and (_etat["csv"].value or _etat["html"].value))
        except Exception:  # noqa: BLE001
            args.areInputsValid = True


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
            ctx.log.exception("Erreur à l'exécution du tableau")
            args.executeFailed = True
            args.executeFailedMessage = ctx.t("erreur.inattendu")


def executer():
    t0 = time.perf_counter()
    design = _etat.get("design")
    if design is None:
        raise fusion_api.ErreurChants("erreur.pas_de_design")
    marge = _marge_mm()
    val = {c: _etat[c].value for c in ("debit", "csv", "html")}
    rg = reglages.lire(ctx.FICHIER_REGLAGES, ctx.t)
    rg.update({"marge": marge, **val})
    reglages.ecrire(ctx.FICHIER_REGLAGES, rg)
    doc = ctx.app.activeDocument.name if ctx.app.activeDocument else "EdgeBanding"
    pieces, _, sorties = ecrire_fichiers(design, doc, marge, val["debit"], val["csv"], val["html"], ctx.t)
    cible = sorties.get("html") or sorties.get("csv")
    if "html" in sorties:
        webbrowser.open(sorties["html"].as_uri())
    elif cible:
        webbrowser.open(cible.parent.as_uri())
    ctx.log.info("Tableau écrit en %.0f ms : %d pièces, %s", (time.perf_counter() - t0) * 1000, len(pieces),
                 {k: str(v) for k, v in sorties.items()})
