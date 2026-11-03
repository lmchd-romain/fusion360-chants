"""Traductions (convention docs/i18n.md de l'écosystème) : en (secours), fr, ja, de ; t(cle, **variables)."""
from __future__ import annotations

import json
from pathlib import Path

LANGUES = ("en", "fr", "ja", "de")
# nom de la valeur d'énumération adsk.core.UserLanguages → code
PAR_NOM_FUSION = {"EnglishLanguage": "en", "FrenchLanguage": "fr", "JapaneseLanguage": "ja", "GermanLanguage": "de"}


def code_langue(nom_fusion: str | None) -> str:
    return PAR_NOM_FUSION.get(nom_fusion or "", "en")


class Textes:
    def __init__(self, dossier: Path, langue: str = "en"):
        self.langue = langue if langue in LANGUES else "en"
        self._tables = {}
        for code in {"en", self.langue}:
            try:
                self._tables[code] = json.loads((Path(dossier) / f"{code}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._tables[code] = {}

    def __call__(self, cle: str, **variables) -> str:
        texte = self._tables.get(self.langue, {}).get(cle) or self._tables["en"].get(cle) or cle
        try:
            return texte.format(**variables)
        except (KeyError, IndexError, ValueError):
            return texte

    def nombre(self, x: float, decimales: int = 1) -> str:
        """Nombre arrondi ; virgule en français et en allemand."""
        s = f"{x:.{decimales}f}"
        return s.replace(".", ",") if self.langue in ("fr", "de") else s
