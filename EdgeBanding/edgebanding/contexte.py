"""État partagé de l'add-in (application, textes, journal, chemins) et garde des handlers."""
from __future__ import annotations

import traceback
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]          # dossier EdgeBanding
RESSOURCES = RACINE / "ressources"
FICHIER_REGLAGES = RACINE / "derniers_reglages.json"
DOSSIER_SORTIE = Path.home() / "Documents" / "EdgeBanding"

app = None
ui = None
t = None      # Textes
log = None
handlers = []  # handlers de l'add-in (vivent jusqu'à stop)


def garde(fn):
    """Exécute fn ; toute exception imprévue part au journal, jamais en boîte de message brute."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        if log:
            log.error("Erreur imprévue :\n%s", traceback.format_exc())
        return None


def texte_erreur(e) -> str:
    return t(e.cle, **e.variables)


def design_actif():
    import adsk.fusion
    return adsk.fusion.Design.cast(app.activeProduct) if app else None
