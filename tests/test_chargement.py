"""L'add-in se charge, démarre et s'arrête avec un faux module adsk (aucun Fusion ici)."""
import importlib
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

import faux_adsk

ENTREE = Path(__file__).resolve().parents[1] / "EdgeBanding" / "EdgeBanding.py"


def _purger():
    for n in [n for n in sys.modules if n == "edgebanding" or n.startswith("edgebanding.")]:
        del sys.modules[n]


@pytest.fixture
def addin(tmp_path, monkeypatch):
    app = faux_adsk.installer()
    _purger()
    spec = importlib.util.spec_from_file_location("EdgeBanding_entree", ENTREE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from edgebanding import contexte, journal
    monkeypatch.setattr(contexte, "RACINE", tmp_path)
    monkeypatch.setattr(contexte, "FICHIER_REGLAGES", tmp_path / "derniers_reglages.json")
    yield mod, app, contexte
    journal.fermer()
    faux_adsk.retirer()
    _purger()


def test_run_cree_les_boutons_et_stop_les_retire(addin):
    mod, app, ctx = addin
    ui = app.userInterface
    ui.commandDefinitions.itemById.return_value = None
    ui.allToolbarPanels.itemById.return_value.controls.itemById.return_value = None
    mod.run({})
    appels = ui.commandDefinitions.addButtonDefinition.call_args_list
    assert [a.args[0] for a in appels] == ["lmchdEdgeBandingPinceau", "lmchdEdgeBandingTableau",
                                           "lmchdEdgeBandingSurbrillanceCmd", "lmchdEdgeBandingRetirerCouleurs"]
    assert appels[0].args[1] == "Edge Banding"  # langue de secours : anglais
    assert appels[0].args[3].replace("\\", "/").endswith("ressources/EdgeBanding")
    for a in appels:
        assert Path(a.args[3], "32x32.png").exists() and Path(a.args[3], "16x16.png").exists()
    ui.allToolbarPanels.itemById.assert_any_call("SolidModifyPanel")
    assert len(ctx.handlers) == 4
    ui.commandDefinitions.itemById.return_value = defn = ui.commandDefinitions.addButtonDefinition.return_value
    mod.stop({})
    defn.deleteMe.assert_called()
    assert ctx.handlers == []


def test_une_commande_secondaire_en_panne_laisse_demarrer(addin):
    mod, app, ctx = addin
    ui = app.userInterface
    ui.commandDefinitions.itemById.return_value = None
    defn = mock.MagicMock()
    ui.commandDefinitions.addButtonDefinition.side_effect = [defn, RuntimeError("panne"), defn, defn]
    mod.run({})
    assert len(ctx.handlers) == 3
    mod.stop({})


def test_tous_les_modules_se_chargent(addin):
    for nom in ("chants", "export", "reglages", "textes", "journal", "contexte", "fusion_api", "interface", "pinceau",
                "tableau", "actions", "recette"):
        importlib.import_module(f"edgebanding.{nom}")


def _commande():
    cmd = mock.MagicMock()
    return cmd


def test_dialogue_pinceau_se_construit(addin):
    mod, app, ctx = addin
    mod.run({})
    from edgebanding import pinceau
    app.activeProduct.findAttributes.return_value = []
    app.activeProduct.attributes.itemByName.return_value = None
    import adsk.fusion
    adsk.fusion.Design.cast.return_value = app.activeProduct
    cmd = _commande()
    pinceau._creer_dialogue(cmd)
    ids = [c.args[0] for c in cmd.commandInputs.addSelectionInput.call_args_list]
    assert ids == ["chants"]
    sel = cmd.commandInputs.addSelectionInput.return_value
    sel.addSelectionFilter.assert_called_with("SolidFaces")
    sel.setSelectionLimits.assert_called_with(0, 0)
    bouton = cmd.commandInputs.addBoolValueInput.call_args
    assert bouton.args[0] == "tous" and bouton.args[2] is False
    assert Path(bouton.args[3], "16x16.png").exists()
    assert len(pinceau.handlers_dialogue) == 6
    mod.stop({})


def test_dialogue_tableau_se_construit(addin):
    mod, app, ctx = addin
    mod.run({})
    from edgebanding import tableau
    app.activeProduct.findAttributes.return_value = []
    app.activeProduct.attributes.itemByName.return_value = None
    import adsk.fusion
    adsk.fusion.Design.cast.return_value = app.activeProduct
    cmd = _commande()
    cmd.commandInputs.addValueInput.return_value.value = 4.0  # 40 mm, en cm
    tableau._creer_dialogue(cmd)
    resume = cmd.commandInputs.addTextBoxCommandInput.return_value
    assert "No banded edge" in resume.text
    mod.stop({})
