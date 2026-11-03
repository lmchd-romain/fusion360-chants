"""Commandes sans dialogue : bascule de la surbrillance, retrait des couleurs. Fusion les exécute dès le clic."""
from __future__ import annotations

import adsk.core

from . import contexte as ctx, fusion_api

_handlers_actions = []


class _Execute(adsk.core.CommandEventHandler):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def notify(self, args):
        try:
            self.fn()
        except fusion_api.ErreurChants as e:
            args.executeFailed = True
            args.executeFailedMessage = ctx.texte_erreur(e)
        except Exception:  # noqa: BLE001
            ctx.log.exception("Erreur à l'exécution")
            args.executeFailed = True
            args.executeFailedMessage = ctx.t("erreur.inattendu")


def _design():
    d = ctx.design_actif()
    if d is None:
        raise fusion_api.ErreurChants("erreur.pas_de_design")
    return d


def surbrillance():
    d = _design()
    allume = fusion_api.basculer_surbrillance(d)
    ctx.log.info("Surbrillance %s", "allumée" if allume else "éteinte")


def retirer():
    d = _design()
    n = fusion_api.retirer_couleurs(d)
    ctx.log.info("Couleurs retirées : %d chants", n)


class _QuandCree(adsk.core.CommandCreatedEventHandler):
    fn = None

    def __init__(self):
        super().__init__()

    def notify(self, args):
        def creer():
            _handlers_actions.clear()
            h = _Execute(type(self).fn)
            args.command.execute.add(h)
            _handlers_actions.append(h)
        ctx.garde(creer)


class QuandCreeSurbrillance(_QuandCree):
    fn = staticmethod(surbrillance)


class QuandCreeRetirer(_QuandCree):
    fn = staticmethod(retirer)
