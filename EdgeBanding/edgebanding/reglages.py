"""Réglages et bibliothèque de chants, en JSON. Pur Python ; toute lecture ratée rend les défauts.

Une référence : {"cle": "abs2-blanc", "nom": "ABS 2 mm blanc", "epaisseur": 2.0, "couleur": "orange"}.
`couleur` est un nom de COULEURS : la couleur d'affichage du chant dans Fusion (repère visuel, pas la teinte réelle).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# couleurs d'affichage : vives, distinctes du bois et des mélaminés courants (mon choix)
COULEURS = {
    "orange": "#FF7A00",
    "jaune": "#FFC400",
    "vert": "#2EAD4B",
    "violet": "#8E44AD",
    "rouge": "#D62828",
    "bleu": "#1F77FF",
    "rose": "#FF4FA3",
    "cyan": "#00B8D9",
    "marron": "#8B5A2B",
    "noir": "#222222",
}

# (clé, clé de texte du nom par défaut, épaisseur mm, couleur) — noms traduits à la première lecture
REFERENCES_DEFAUT = [
    ("abs2-blanc", "ref.abs2_blanc", 2.0, "orange"),
    ("abs08-blanc", "ref.abs08_blanc", 0.8, "jaune"),
    ("abs2-noir", "ref.abs2_noir", 2.0, "violet"),
    ("chene06", "ref.chene06", 0.6, "vert"),
    ("noyer06", "ref.noyer06", 0.6, "rouge"),
]

MODES = ("couleur", "aucune")  # couleur posée sur les faces / aucune (surbrillance à la demande)

DEFAUTS = {
    "reference": "abs2-blanc",
    "mode": "couleur",
    "marge": 40.0,       # mm ajoutés à chaque chant au tableau (20 mm de débord à chaque bout)
    "debit": False,
    "csv": True,
    "html": True,
}


def bibliotheque_defaut(t) -> list[dict]:
    return [{"cle": c, "nom": t(k), "epaisseur": e, "couleur": col} for c, k, e, col in REFERENCES_DEFAUT]


def _reference_valide(r) -> bool:
    return (isinstance(r, dict) and isinstance(r.get("cle"), str) and r["cle"]
            and isinstance(r.get("nom"), str) and r["nom"].strip()
            and isinstance(r.get("epaisseur"), (int, float)) and not isinstance(r.get("epaisseur"), bool)
            and 0 < r["epaisseur"] <= 20 and r.get("couleur") in COULEURS)


def lire(chemin: Path, t) -> dict:
    r = dict(DEFAUTS)
    r["bibliotheque"] = bibliotheque_defaut(t)
    try:
        lu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return r
    if not isinstance(lu, dict):
        return r
    biblio = lu.get("bibliotheque")
    if isinstance(biblio, list):
        bonnes = [dict(x, epaisseur=float(x["epaisseur"])) for x in biblio if _reference_valide(x)]
        cles = [x["cle"] for x in bonnes]
        if bonnes and len(set(cles)) == len(cles):
            r["bibliotheque"] = bonnes
    for cle, defaut in DEFAUTS.items():
        v = lu.get(cle)
        if isinstance(defaut, bool):
            if isinstance(v, bool):
                r[cle] = v
        elif cle == "mode":
            if v in MODES:
                r[cle] = v
        elif cle == "reference":
            if isinstance(v, str) and any(x["cle"] == v for x in r["bibliotheque"]):
                r[cle] = v
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1000:
            r[cle] = float(v)
    if not any(x["cle"] == r["reference"] for x in r["bibliotheque"]):
        r["reference"] = r["bibliotheque"][0]["cle"]
    return r


def ecrire(chemin: Path, reglages: dict) -> None:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(reglages, ensure_ascii=False, indent=2), encoding="utf-8")


def nouvelle_cle(bibliotheque: list[dict], nom: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-") or "ref"
    cles = {x["cle"] for x in bibliotheque}
    if base not in cles:
        return base
    i = 2
    while f"{base}-{i}" in cles:
        i += 1
    return f"{base}-{i}"


def hexa(couleur: str) -> str:
    return COULEURS.get(couleur, COULEURS["orange"])


def rvb(hexa_couleur: str) -> tuple[int, int, int]:
    h = hexa_couleur.lstrip("#")
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        return 255, 122, 0
