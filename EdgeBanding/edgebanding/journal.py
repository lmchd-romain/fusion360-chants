"""Journal fichier (journal.log, 1 Mo × 2) : fait foi, la fenêtre Text Commands n'affiche que si elle est ouverte.

Le gestionnaire du plugin est marqué (`_edgebanding`) : on ne teste et ne retire que celui-là (leçon Assemblage).
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

NOM = "edgebanding"


def ouvrir(dossier: Path) -> logging.Logger:
    log = logging.getLogger(NOM)
    if not any(getattr(h, "_edgebanding", False) for h in log.handlers):
        Path(dossier).mkdir(parents=True, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(Path(dossier) / "journal.log", maxBytes=1_000_000, backupCount=2,
                                                 encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        h._edgebanding = True
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def fermer() -> None:
    log = logging.getLogger(NOM)
    for h in list(log.handlers):
        if getattr(h, "_edgebanding", False):
            h.close()
            log.removeHandler(h)
