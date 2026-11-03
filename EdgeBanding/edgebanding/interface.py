"""Boutons de l'add-in : SOLIDE → Modifier. « Chants plaqués » promu ; tableau, surbrillance, retrait des couleurs
dans le menu du panneau (mon choix). Une commande secondaire en panne laisse démarrer les autres.
"""
from __future__ import annotations

import adsk.core

from . import VERSION, contexte as ctx, journal
from . import recette  # noqa: F401 — chargée pour être jouée par le connecteur Fusion MCP
from .textes import Textes, code_langue

ID_PANNEAU = "SolidModifyPanel"
ID_PINCEAU = "lmchdEdgeBandingPinceau"
ID_TABLEAU = "lmchdEdgeBandingTableau"
ID_SURBRILLANCE = "lmchdEdgeBandingSurbrillanceCmd"
ID_RETIRER = "lmchdEdgeBandingRetirerCouleurs"

# (id, clé de texte, dossier d'icônes, promu)
COMMANDES = [
    (ID_PINCEAU, "pinceau", "EdgeBanding", True),
    (ID_TABLEAU, "tableau", "Tableau", False),
    (ID_SURBRILLANCE, "surbrillance", "Surbrillance", False),
    (ID_RETIRER, "retirer", "RetirerCouleurs", False),
]


def _langue(app) -> str:
    try:
        valeur = app.preferences.generalPreferences.userLanguage
        for nom in ("FrenchLanguage", "JapaneseLanguage", "GermanLanguage", "EnglishLanguage"):
            if getattr(adsk.core.UserLanguages, nom, object()) == valeur:
                return code_langue(nom)
    except Exception:  # noqa: BLE001
        pass
    return "en"


def _handler_creation(cle):
    from . import pinceau, tableau, actions
    return {"pinceau": pinceau.QuandCree, "tableau": tableau.QuandCree,
            "surbrillance": actions.QuandCreeSurbrillance, "retirer": actions.QuandCreeRetirer}[cle]()


def demarrer():
    ctx.app = adsk.core.Application.get()
    ctx.ui = ctx.app.userInterface
    ctx.log = journal.ouvrir(ctx.RACINE)
    ctx.t = Textes(ctx.RESSOURCES / "langues", _langue(ctx.app))
    arreter_interface()  # restes d'un arrêt incomplet
    panneau = ctx.ui.allToolbarPanels.itemById(ID_PANNEAU)
    for ident, cle, dossier, promu in COMMANDES:
        try:
            defn = ctx.ui.commandDefinitions.addButtonDefinition(
                ident, ctx.t(f"{cle}.nom"), ctx.t(f"{cle}.infobulle"), str(ctx.RESSOURCES / dossier))
            h = _handler_creation(cle)
            defn.commandCreated.add(h)
            ctx.handlers.append(h)
            if panneau:
                ctrl = panneau.controls.addCommand(defn)
                ctrl.isPromoted = promu
        except Exception:  # noqa: BLE001
            ctx.log.exception("Commande %s non créée", ident)
            if ident == ID_PINCEAU:
                raise
    ctx.log.info("EdgeBanding %s démarré (langue %s)", VERSION, ctx.t.langue)


def arreter_interface():
    if ctx.ui is None:
        return
    panneau = ctx.ui.allToolbarPanels.itemById(ID_PANNEAU)
    for ident, *_ in reversed(COMMANDES):
        if panneau:
            c = panneau.controls.itemById(ident)
            if c:
                c.deleteMe()
        d = ctx.ui.commandDefinitions.itemById(ident)
        if d:
            d.deleteMe()


def arreter():
    from . import pinceau
    arreter_interface()
    ctx.handlers.clear()
    pinceau.handlers_dialogue.clear()
    if ctx.log:
        ctx.log.info("EdgeBanding arrêté")
    journal.fermer()
